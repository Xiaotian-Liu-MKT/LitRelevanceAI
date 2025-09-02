import json
from unittest.mock import MagicMock

import pandas as pd

from litrx.abstract_screener import analyze_article, prepare_dataframe


OPEN_QUESTIONS = [
    {"key": "open1", "question": "请总结", "column_name": "open1_col"}
]

YES_NO_QUESTIONS = [
    {"key": "crit1", "question": "是否相关?", "column_name": "crit1_col"}
]


def make_response(payload):
    return {
        "choices": [
            {"message": {"content": json.dumps(payload, ensure_ascii=False)}}
        ]
    }


def setup_dataframe() -> pd.DataFrame:
    df = pd.DataFrame({"Title": ["t"], "Abstract": ["a"]})
    return prepare_dataframe(df, OPEN_QUESTIONS, YES_NO_QUESTIONS)


def test_verification_populates_verified_columns():
    df = setup_dataframe()
    initial_payload = {
        "quick_analysis": {"open1": "analysis"},
        "screening_results": {"crit1": "是"},
    }
    verification_payload = {
        "quick_analysis": {"open1": "是"},
        "screening_results": {"crit1": "否"},
    }
    client = MagicMock()
    client.request = MagicMock(
        side_effect=[make_response(initial_payload), make_response(verification_payload)]
    )

    analyze_article(
        df,
        0,
        df.iloc[0],
        "Title",
        "Abstract",
        OPEN_QUESTIONS,
        YES_NO_QUESTIONS,
        {"ENABLE_VERIFICATION": True},
        client,
    )

    assert df.at[0, "open1_col_verified"] == "是"
    assert df.at[0, "crit1_col_verified"] == "否"


def test_verification_error_sets_failure_message():
    df = setup_dataframe()
    initial_payload = {
        "quick_analysis": {"open1": "analysis"},
        "screening_results": {"crit1": "是"},
    }
    client = MagicMock()
    client.request = MagicMock(
        side_effect=[make_response(initial_payload), Exception("boom")]
    )

    analyze_article(
        df,
        0,
        df.iloc[0],
        "Title",
        "Abstract",
        OPEN_QUESTIONS,
        YES_NO_QUESTIONS,
        {"ENABLE_VERIFICATION": True},
        client,
    )

    assert df.at[0, "open1_col_verified"] == "验证失败"
    assert df.at[0, "crit1_col_verified"] == "验证失败"
