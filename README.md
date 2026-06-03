# 東京都 観光インフラダッシュボード

東京都オープンデータAPIからFREE Wi-Fi & TOKYOの位置情報を取得し、Streamlitで可視化するシンプルなデモです。

## 起動方法

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## 利用API

- 東京都オープンデータAPI
- 公衆無線LANアクセスポイント一覧

API仕様:
https://spec.api.metro.tokyo.lg.jp/spec/t000029d0000000025-a9cf23fb2e2944f5f5e8e535b537f61d-0

## デモの見せ方

1. Web APIへPOSTしてJSONを取得する
2. JSONの`hits`を表形式に変換する
3. 住所から市区町村を抽出する
4. 地図、KPI、棒グラフ、ツリーマップで概要を見せる
5. Power BIでも同じ考え方でWeb API取得ができることを紹介する
