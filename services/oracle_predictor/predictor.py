"""ORACLE Predictor — универсальный предиктивный движок.

Автоматически определяет тип задачи по данным и запускает подходящую модель:
- classification → GradientBoosting, LogisticRegression
- regression → GradientBoosting, Ridge
- timeseries → Trend decomposition + FFT seasonality
- anomaly_detection → IsolationForest + Z-score
- survival → Weibull distribution
"""
from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.fft import fft, fftfreq
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, IsolationForest
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger("oracle.predictor")

TASK_TYPES = ("classification", "regression", "timeseries", "anomaly_detection", "survival")


class OraclePredictor:
    """Универсальный предиктивный движок."""

    def predict(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        force_type: Optional[str] = None,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """Главная точка входа: принимает DataFrame, возвращает результат."""
        eda = self._eda(df)

        if force_type and force_type in TASK_TYPES:
            task_type = force_type
        else:
            task_type = self._detect_task_type(df, target_col)

        if task_type == "timeseries":
            results = self._train_timeseries(df, target_col, forecast_periods)
        elif task_type == "anomaly_detection":
            X, _, feature_names = self._preprocess(df, target_col=None)
            results = self._train_anomaly(X, feature_names)
        elif task_type == "survival":
            results = self._train_survival(df, target_col)
        elif task_type == "classification":
            X, y, feature_names = self._preprocess(df, target_col)
            results = self._train_classification(X, y, feature_names)
        else:  # regression
            X, y, feature_names = self._preprocess(df, target_col)
            results = self._train_regression(X, y, feature_names)

        report = self._generate_report(eda, task_type, results)

        return {
            "task_type": task_type,
            "eda_summary": eda,
            "metrics": results.get("metrics", {}),
            "predictions": results.get("predictions", []),
            "best_model": results.get("best_model", ""),
            "report": report,
        }

    # ── Автоопределение типа задачи ───────────────────────────────────────────

    def _detect_task_type(self, df: pd.DataFrame, target_col: Optional[str]) -> str:
        # Проверяем наличие столбца с датами
        date_cols = [c for c in df.columns if df[c].dtype == "datetime64[ns]"]
        if not date_cols:
            for c in df.columns:
                if df[c].dtype == object:
                    try:
                        pd.to_datetime(df[c], infer_datetime_format=True)
                        date_cols.append(c)
                    except (ValueError, TypeError):
                        pass

        # Если есть дата и числовой таргет — временной ряд
        if date_cols and target_col:
            if target_col in df.columns and pd.api.types.is_numeric_dtype(df[target_col]):
                return "timeseries"

        # Нет таргета — аномалии
        if not target_col or target_col not in df.columns:
            return "anomaly_detection"

        series = df[target_col]

        # survival: ключевые слова в названии + положительные числа
        survival_hints = ("ttf", "time_to", "days_to", "lifetime", "duration", "failure", "survival")
        if any(h in target_col.lower() for h in survival_hints) and pd.api.types.is_numeric_dtype(series):
            return "survival"

        # classification: категориальный или мало уникальных значений
        if not pd.api.types.is_numeric_dtype(series):
            return "classification"

        n_unique = series.nunique()
        if n_unique <= 10:
            return "classification"
        if n_unique <= 20 and n_unique / len(df) < 0.05:
            return "classification"

        return "regression"

    # ── EDA ────────────────────────────────────────────────────────────────────

    def _eda(self, df: pd.DataFrame) -> dict[str, Any]:
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        corr = {}
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            # Топ-5 корреляций
            pairs = []
            for i, c1 in enumerate(numeric_cols):
                for c2 in numeric_cols[i + 1:]:
                    pairs.append((c1, c2, abs(corr_matrix.loc[c1, c2])))
            pairs.sort(key=lambda x: x[2], reverse=True)
            corr = {f"{p[0]} ↔ {p[1]}": round(p[2], 3) for p in pairs[:5]}

        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
            "missing": {c: int(v) for c, v in missing.items() if v > 0},
            "missing_pct": {c: float(v) for c, v in missing_pct.items() if v > 0},
            "numeric_stats": json.loads(df.describe().to_json()) if len(numeric_cols) > 0 else {},
            "top_correlations": corr,
        }

    # ── Препроцессинг ─────────────────────────────────────────────────────────

    def _preprocess(
        self, df: pd.DataFrame, target_col: Optional[str]
    ) -> tuple[np.ndarray, Optional[np.ndarray], list[str]]:
        df = df.copy()

        # Убираем дату-столбцы
        for c in df.columns:
            if df[c].dtype == "datetime64[ns]":
                df.drop(columns=[c], inplace=True)
            elif df[c].dtype == object:
                try:
                    pd.to_datetime(df[c], infer_datetime_format=True)
                    df.drop(columns=[c], inplace=True)
                except (ValueError, TypeError):
                    pass

        y = None
        if target_col and target_col in df.columns:
            y_series = df[target_col]
            df.drop(columns=[target_col], inplace=True)
            if pd.api.types.is_numeric_dtype(y_series):
                y = y_series.values
            else:
                le = LabelEncoder()
                y = le.fit_transform(y_series.fillna("__missing__"))

        # Заполняем пропуски
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                df[c].fillna(df[c].median(), inplace=True)
            else:
                df[c].fillna(df[c].mode().iloc[0] if len(df[c].mode()) > 0 else "__missing__", inplace=True)

        # Кодируем категориальные
        cat_cols = df.select_dtypes(include=["object", "category"]).columns
        for c in cat_cols:
            le = LabelEncoder()
            df[c] = le.fit_transform(df[c].astype(str))

        feature_names = df.columns.tolist()

        # Скейлинг
        scaler = StandardScaler()
        X = scaler.fit_transform(df.values)

        return X, y, feature_names

    # ── Classification ────────────────────────────────────────────────────────

    def _train_classification(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str]
    ) -> dict[str, Any]:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        models = {
            "GradientBoosting": GradientBoostingClassifier(
                n_estimators=100, max_depth=5, random_state=42
            ),
            "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        }

        results = {}
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            cv_scores = cross_val_score(model, X, y, cv=5, scoring="f1_weighted")
            results[name] = {
                "accuracy": round(accuracy_score(y_test, y_pred), 4),
                "f1_weighted": round(f1_score(y_test, y_pred, average="weighted"), 4),
                "cv_f1_mean": round(cv_scores.mean(), 4),
                "cv_f1_std": round(cv_scores.std(), 4),
                "predictions": y_pred.tolist(),
            }

        best_name = max(results, key=lambda k: results[k]["f1_weighted"])
        best = results[best_name]

        # Feature importance для лучшей модели
        best_model = models[best_name]
        importances = {}
        if hasattr(best_model, "feature_importances_"):
            imp = best_model.feature_importances_
            importances = {feature_names[i]: round(float(imp[i]), 4) for i in np.argsort(imp)[::-1][:10]}
        elif hasattr(best_model, "coef_"):
            imp = np.abs(best_model.coef_[0]) if best_model.coef_.ndim > 1 else np.abs(best_model.coef_)
            importances = {feature_names[i]: round(float(imp[i]), 4) for i in np.argsort(imp)[::-1][:10]}

        return {
            "best_model": best_name,
            "metrics": {
                "accuracy": best["accuracy"],
                "f1_weighted": best["f1_weighted"],
                "cv_f1_mean": best["cv_f1_mean"],
                "cv_f1_std": best["cv_f1_std"],
            },
            "all_models": {k: {kk: vv for kk, vv in v.items() if kk != "predictions"} for k, v in results.items()},
            "feature_importance": importances,
            "predictions": best["predictions"],
        }

    # ── Regression ────────────────────────────────────────────────────────────

    def _train_regression(
        self, X: np.ndarray, y: np.ndarray, feature_names: list[str]
    ) -> dict[str, Any]:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        models = {
            "GradientBoosting": GradientBoostingRegressor(
                n_estimators=100, max_depth=5, random_state=42
            ),
            "Ridge": Ridge(alpha=1.0),
        }

        results = {}
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
            results[name] = {
                "r2": round(r2_score(y_test, y_pred), 4),
                "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 4),
                "mae": round(mean_absolute_error(y_test, y_pred), 4),
                "cv_r2_mean": round(cv_scores.mean(), 4),
                "cv_r2_std": round(cv_scores.std(), 4),
                "predictions": y_pred.tolist(),
            }

        best_name = max(results, key=lambda k: results[k]["r2"])
        best = results[best_name]

        best_model = models[best_name]
        importances = {}
        if hasattr(best_model, "feature_importances_"):
            imp = best_model.feature_importances_
            importances = {feature_names[i]: round(float(imp[i]), 4) for i in np.argsort(imp)[::-1][:10]}
        elif hasattr(best_model, "coef_"):
            imp = np.abs(best_model.coef_)
            importances = {feature_names[i]: round(float(imp[i]), 4) for i in np.argsort(imp)[::-1][:10]}

        return {
            "best_model": best_name,
            "metrics": {
                "r2": best["r2"],
                "rmse": best["rmse"],
                "mae": best["mae"],
                "cv_r2_mean": best["cv_r2_mean"],
                "cv_r2_std": best["cv_r2_std"],
            },
            "all_models": {k: {kk: vv for kk, vv in v.items() if kk != "predictions"} for k, v in results.items()},
            "feature_importance": importances,
            "predictions": best["predictions"],
        }

    # ── Time Series ───────────────────────────────────────────────────────────

    def _train_timeseries(
        self, df: pd.DataFrame, target_col: str, forecast_periods: int = 30
    ) -> dict[str, Any]:
        df = df.copy()

        # Находим дата-столбец
        date_col = None
        for c in df.columns:
            if df[c].dtype == "datetime64[ns]":
                date_col = c
                break
        if not date_col:
            for c in df.columns:
                if df[c].dtype == object:
                    try:
                        df[c] = pd.to_datetime(df[c], infer_datetime_format=True)
                        date_col = c
                        break
                    except (ValueError, TypeError):
                        pass

        if not date_col:
            return {"metrics": {}, "predictions": [], "best_model": "timeseries_failed"}

        df = df.sort_values(date_col).reset_index(drop=True)
        values = df[target_col].fillna(method="ffill").fillna(0).values.astype(float)
        n = len(values)
        t = np.arange(n)

        # Тренд: полиномиальная регрессия
        coeffs = np.polyfit(t, values, deg=min(2, n - 1))
        trend = np.polyval(coeffs, t)
        residuals = values - trend

        # Сезонность: FFT
        fft_vals = fft(residuals)
        freqs = fftfreq(n)
        # Берём топ-3 частоты (кроме 0)
        magnitudes = np.abs(fft_vals)
        magnitudes[0] = 0  # убираем DC
        top_indices = np.argsort(magnitudes)[::-1][:6]  # топ-3 пары

        seasonal = np.zeros(n)
        for idx in top_indices:
            if freqs[idx] > 0:
                amp = magnitudes[idx] / n * 2
                phase = np.angle(fft_vals[idx])
                seasonal += amp * np.cos(2 * np.pi * freqs[idx] * t + phase)

        fitted = trend + seasonal

        # Метрики на обучающих данных
        rmse = float(np.sqrt(np.mean((values - fitted) ** 2)))
        mae = float(np.mean(np.abs(values - fitted)))

        # Прогноз
        t_future = np.arange(n, n + forecast_periods)
        trend_future = np.polyval(coeffs, t_future)
        seasonal_future = np.zeros(forecast_periods)
        for idx in top_indices:
            if freqs[idx] > 0:
                amp = magnitudes[idx] / n * 2
                phase = np.angle(fft_vals[idx])
                seasonal_future += amp * np.cos(2 * np.pi * freqs[idx] * t_future + phase)

        forecast = trend_future + seasonal_future

        # Даты для прогноза
        last_date = df[date_col].iloc[-1]
        freq = pd.infer_freq(df[date_col])
        if freq:
            future_dates = pd.date_range(start=last_date, periods=forecast_periods + 1, freq=freq)[1:]
        else:
            delta = (df[date_col].iloc[-1] - df[date_col].iloc[0]) / max(n - 1, 1)
            future_dates = [last_date + delta * (i + 1) for i in range(forecast_periods)]

        predictions = [
            {"date": str(d.date()) if hasattr(d, "date") else str(d), "value": round(float(v), 2)}
            for d, v in zip(future_dates, forecast)
        ]

        return {
            "best_model": "Trend+FFT",
            "metrics": {
                "rmse_train": round(rmse, 4),
                "mae_train": round(mae, 4),
                "trend_coefficients": [round(float(c), 6) for c in coeffs],
                "data_points": n,
                "forecast_periods": forecast_periods,
            },
            "predictions": predictions,
        }

    # ── Anomaly Detection ─────────────────────────────────────────────────────

    def _train_anomaly(
        self, X: np.ndarray, feature_names: list[str]
    ) -> dict[str, Any]:
        # IsolationForest
        iso = IsolationForest(contamination=0.05, random_state=42)
        iso_labels = iso.fit_predict(X)  # 1 = normal, -1 = anomaly
        iso_scores = iso.score_samples(X)

        # Z-score
        z_scores = np.abs(scipy_stats.zscore(X, axis=0))
        z_anomaly = (z_scores > 3).any(axis=1).astype(int)  # 1 = anomaly по z-score

        # Комбинируем: аномалия если хотя бы один метод нашёл
        combined = np.where((iso_labels == -1) | (z_anomaly == 1), 1, 0)

        n_anomalies_iso = int((iso_labels == -1).sum())
        n_anomalies_z = int(z_anomaly.sum())
        n_anomalies_combined = int(combined.sum())

        # Индексы аномалий
        anomaly_indices = np.where(combined == 1)[0].tolist()

        return {
            "best_model": "IsolationForest+Z-score",
            "metrics": {
                "total_samples": len(X),
                "anomalies_isolation_forest": n_anomalies_iso,
                "anomalies_z_score": n_anomalies_z,
                "anomalies_combined": n_anomalies_combined,
                "anomaly_rate": round(n_anomalies_combined / len(X), 4),
            },
            "predictions": anomaly_indices[:100],  # первые 100 индексов аномалий
            "anomaly_scores": [round(float(s), 4) for s in iso_scores[:100]],
        }

    # ── Survival Analysis ─────────────────────────────────────────────────────

    def _train_survival(
        self, df: pd.DataFrame, target_col: str
    ) -> dict[str, Any]:
        times = df[target_col].dropna().values.astype(float)
        times = times[times > 0]

        if len(times) < 5:
            return {"metrics": {}, "predictions": [], "best_model": "survival_failed"}

        # Weibull MLE
        shape, loc, scale = scipy_stats.weibull_min.fit(times, floc=0)

        # Survival function S(t) = exp(-(t/scale)^shape)
        t_grid = np.linspace(0, float(times.max()) * 1.5, 100)
        survival_fn = scipy_stats.weibull_min.sf(t_grid, shape, loc=0, scale=scale)
        hazard_fn = (shape / scale) * (t_grid / scale) ** (shape - 1)

        # Статистики
        mean_lifetime = scipy_stats.weibull_min.mean(shape, loc=0, scale=scale)
        median_lifetime = scipy_stats.weibull_min.median(shape, loc=0, scale=scale)

        predictions = [
            {"time": round(float(t), 2), "survival_prob": round(float(s), 4), "hazard": round(float(h), 6)}
            for t, s, h in zip(t_grid[::5], survival_fn[::5], hazard_fn[::5])
        ]

        return {
            "best_model": "Weibull",
            "metrics": {
                "shape": round(float(shape), 4),
                "scale": round(float(scale), 4),
                "mean_lifetime": round(float(mean_lifetime), 2),
                "median_lifetime": round(float(median_lifetime), 2),
                "data_points": len(times),
                "min_time": round(float(times.min()), 2),
                "max_time": round(float(times.max()), 2),
            },
            "predictions": predictions,
        }

    # ── Генерация отчёта ──────────────────────────────────────────────────────

    def _generate_report(
        self, eda: dict, task_type: str, results: dict
    ) -> str:
        lines = [
            "# ORACLE — Отчёт предиктивного анализа",
            "",
            f"## Тип задачи: {task_type}",
            f"## Лучшая модель: {results.get('best_model', '—')}",
            "",
            "## EDA (разведочный анализ)",
            f"- Строк: {eda['rows']}",
            f"- Столбцов: {eda['columns']}",
        ]

        if eda.get("missing"):
            lines.append("- Пропуски:")
            for col, cnt in eda["missing"].items():
                pct = eda["missing_pct"].get(col, 0)
                lines.append(f"  - {col}: {cnt} ({pct}%)")

        if eda.get("top_correlations"):
            lines.append("- Топ корреляции:")
            for pair, val in eda["top_correlations"].items():
                lines.append(f"  - {pair}: {val}")

        lines.extend(["", "## Метрики"])
        for k, v in results.get("metrics", {}).items():
            lines.append(f"- {k}: {v}")

        if results.get("feature_importance"):
            lines.extend(["", "## Важность признаков"])
            for feat, imp in results["feature_importance"].items():
                lines.append(f"- {feat}: {imp}")

        if results.get("predictions"):
            preds = results["predictions"]
            lines.extend(["", f"## Предсказания (первые {min(10, len(preds))})"])
            for p in preds[:10]:
                if isinstance(p, dict):
                    lines.append(f"- {p}")
                else:
                    lines.append(f"- {p}")

        return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python predictor.py <file.csv> <target_column> [force_type] [forecast_periods]")
        sys.exit(1)

    file_path = sys.argv[1]
    target = sys.argv[2]
    force = sys.argv[3] if len(sys.argv) > 3 else None
    periods = int(sys.argv[4]) if len(sys.argv) > 4 else 30

    if file_path.endswith((".xlsx", ".xls")):
        data = pd.read_excel(file_path)
    else:
        data = pd.read_csv(file_path)

    oracle = OraclePredictor()
    result = oracle.predict(data, target, force_type=force, forecast_periods=periods)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
