import os
import sys
import json
import datetime as dt
import streamlit as st
import pandas as pd
import altair as alt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(BASE_DIR))
try:
    from tts.fallback import simplify_text, synthesize_local
except Exception:
    simplify_text = lambda x: x
    def synthesize_local(text, voice='default', tone='calm', lang='en', out_path=None):
        return None

def load_weekly_report():
    path = os.path.join(BASE_DIR, 'exports', 'weekly_report.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items') or []
        return items
    except Exception:
        return []

def fetch_sample(host='127.0.0.1', port=8500):
    url = f'http://{host}:{port}/processed/sample'
    try:
        r = requests.get(url, timeout=5)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None

def read_audio_bytes(path):
    try:
        if not path:
            return None
        full = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
        if not os.path.exists(full):
            return None
        with open(full, 'rb') as f:
            return f.read()
    except Exception:
        return None

def get_or_synthesize_audio(item, avatar='streamlit'):
    path = item.get('audio_path')
    data = read_audio_bytes(path)
    if data:
        return data
    text = item.get('summary_medium') or item.get('summary_short') or item.get('script') or item.get('title') or ''
    if not text:
        return None
    simp = simplify_text(text)
    slug = str(item.get('id') or item.get('title') or 'sample').replace('/', '_').replace('\\','_')[:40]
    out_dir = os.path.join(BASE_DIR, 'data', 'audio', 'streamlit')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{slug}_{avatar}.wav")
    res = synthesize_local(simp, voice='default', tone=item.get('tone') or 'calm', lang=item.get('language') or 'en', out_path=out_path)
    if isinstance(res, str) and os.path.exists(res):
        item['audio_path'] = os.path.relpath(res, BASE_DIR).replace('\\','/')
        return read_audio_bytes(item['audio_path'])
    return None

st.set_page_config(page_title='Insight Node Output', layout='wide')
st.title('Insight Narrator Node — Project Output')
st.caption('Ingest → Summarize → Sentiment → TTS → Rank → Export → Feedback')

source = st.sidebar.radio('Data Source', ['Weekly Report', 'Staging Endpoint'])
host = st.sidebar.text_input('API Host', '127.0.0.1')
port = st.sidebar.number_input('API Port', value=8500, step=1)

if source == 'Weekly Report':
    items = load_weekly_report()
    if not items:
        st.warning('No weekly report found. Run pipeline or smart_feed first.')
    else:
        df = pd.DataFrame(items)
        if 'timestamp' in df.columns:
            try:
                df['ts'] = pd.to_datetime(df['timestamp'])
            except Exception:
                df['ts'] = pd.NaT
        else:
            df['ts'] = pd.NaT
        df['trend_score'] = pd.to_numeric(df.get('trend_score', 0.0), errors='coerce').fillna(0.0)
        df['priority_score'] = pd.to_numeric(df.get('priority_score', 0.0), errors='coerce').fillna(0.0)
        conf1 = pd.to_numeric(df['confidence_score'], errors='coerce') if 'confidence_score' in df.columns else pd.Series([None]*len(df))
        conf2 = pd.to_numeric(df['confidence'], errors='coerce') if 'confidence' in df.columns else pd.Series([None]*len(df))
        df['confidence_score'] = conf1.fillna(conf2).fillna(0.0)

        cats = sorted([c for c in df.get('category', pd.Series()).dropna().unique().tolist()]) if 'category' in df.columns else []
        langs = sorted([c for c in df.get('language', pd.Series()).dropna().unique().tolist()]) if 'language' in df.columns else []
        tones = sorted([c for c in df.get('tone', pd.Series()).dropna().unique().tolist()]) if 'tone' in df.columns else []
        sel_cat = st.sidebar.multiselect('Filter Category', cats, default=[])
        sel_lang = st.sidebar.multiselect('Filter Language', langs, default=[])
        sel_tone = st.sidebar.multiselect('Filter Tone', tones, default=[])
        df_f = df.copy()
        if len(sel_cat) > 0:
            df_f = df_f[df_f['category'].isin(sel_cat)]
        if len(sel_lang) > 0:
            df_f = df_f[df_f['language'].isin(sel_lang)]
        if len(sel_tone) > 0:
            df_f = df_f[df_f['tone'].fillna('unknown').isin(sel_tone)]
        if df['ts'].notna().any():
            min_d = df['ts'].min().date()
            max_d = df['ts'].max().date()
            date_range = st.sidebar.date_input('Filter Date Range', (min_d, max_d))
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                df_f = df_f[df_f['ts'].dt.date.between(start, end)]
        if len(df_f) == 0:
            st.warning('No items matched filters.')
            st.stop()

        st.subheader('Overview Charts')
        cA, cB = st.columns(2)
        with cA:
            if df_f['ts'].notna().any():
                ts_df = df_f.dropna(subset=['ts']).copy()
                ts_df['date'] = ts_df['ts'].dt.date
                agg = ts_df.groupby('date', as_index=False)['trend_score'].mean()
                chart = alt.Chart(agg).mark_line(point=True).encode(x='date:T', y='trend_score:Q').properties(height=250)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info('No timestamp data available for trend over time.')
        with cB:
            tone_df = df_f.copy()
            tone_df['tone'] = tone_df.get('tone').fillna('unknown')
            tone_counts = tone_df.groupby('tone', as_index=False).size()
            chart2 = alt.Chart(tone_counts).mark_bar().encode(x='tone:N', y='size:Q').properties(height=250)
            st.altair_chart(chart2, use_container_width=True)

        st.subheader('More Charts')
        cC, cD = st.columns(2)
        with cC:
            if df_f['ts'].notna().any():
                ts_df = df_f.dropna(subset=['ts']).copy()
                ts_df['date'] = ts_df['ts'].dt.date
                agg_conf = ts_df.groupby('date', as_index=False)['confidence_score'].mean()
                chart_conf = alt.Chart(agg_conf).mark_line(point=True).encode(x='date:T', y='confidence_score:Q').properties(height=250)
                st.altair_chart(chart_conf, use_container_width=True)
            else:
                st.info('No timestamp data available for confidence over time.')
        with cD:
            tp_df = df_f.copy()
            tp_df['tone'] = tp_df.get('tone').fillna('unknown')
            agg_tp = tp_df.groupby('tone', as_index=False)['priority_score'].mean()
            chart_tp = alt.Chart(agg_tp).mark_bar().encode(x='tone:N', y='priority_score:Q').properties(height=250)
            st.altair_chart(chart_tp, use_container_width=True)

        st.subheader('Scatter: Priority vs Trend by Tone')
        scat_df = df_f.copy()
        scat_df['tone'] = scat_df.get('tone').fillna('unknown')
        chart_scat = alt.Chart(scat_df).mark_circle(size=80).encode(
            x=alt.X('priority_score:Q', title='Priority Score'),
            y=alt.Y('trend_score:Q', title='Trend Score'),
            color=alt.Color('tone:N', legend=alt.Legend(title='Tone')),
            tooltip=['title:N','priority_score:Q','trend_score:Q','tone:N']
        ).properties(height=300)
        st.altair_chart(chart_scat, use_container_width=True)

        indices = df_f.index.tolist()
        labels = {i: f"{items[i].get('title','Untitled')[:80]}" for i in indices}
        idx = st.selectbox('Select Item', indices, format_func=lambda i: labels.get(i, str(i)))
        item = items[idx]

        left, right = st.columns([2,1])
        with left:
            st.subheader(item.get('title'))
            st.write(f"Category: {item.get('category')} | Language: {item.get('language')}")
            st.write(f"Polarity: {item.get('polarity')} | Tone: {item.get('tone')}")
            st.write(f"Timestamp: {item.get('timestamp')}")
            st.text_area('Script (summary_medium)', item.get('summary_medium') or item.get('summary_short') or '', height=180)
        with right:
            st.metric('Trend Score', f"{item.get('trend_score', 0.0)}")
            st.metric('Priority Score', f"{item.get('priority_score', 0.0)}")
            st.metric('Confidence Score', f"{item.get('confidence_score', item.get('confidence', 0.0))}")

        audio_bytes = read_audio_bytes(item.get('audio_path')) or get_or_synthesize_audio(item)
        if audio_bytes:
            st.audio(audio_bytes, format='audio/wav')
        else:
            st.info('No audio available for this item.')

        st.divider()
        st.subheader('RL Feedback Simulation')
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            like = st.button('👍 user_like')
        with c2:
            skip = st.button('⏭️ user_skip')
        with c3:
            approve = st.button('✅ editor_approve')
        with c4:
            flag = st.button('🚩 manual_override')
        if like or skip or approve or flag:
            signals = {
                'user_like': like,
                'user_skip': skip,
                'editor_approve': approve,
                'manual_override': flag
            }
            try:
                r = requests.post(f'http://{host}:{port}/feedback', json={'id': item.get('id'), 'item': {'priority_score': item.get('priority_score', 0.0)}, 'signals': signals}, timeout=5)
                if r.ok:
                    st.success(r.json())
                else:
                    st.error(f'Feedback failed: {r.status_code}')
            except Exception as e:
                st.error(f'Feedback error: {e}')

else:
    sample = fetch_sample(host=host, port=port)
    if not sample:
        st.warning('Staging endpoint not reachable or returned no data.')
    else:
        items = load_weekly_report()
        df = pd.DataFrame(items)
        if 'timestamp' in df.columns:
            try:
                df['ts'] = pd.to_datetime(df['timestamp'])
            except Exception:
                df['ts'] = pd.NaT
        else:
            df['ts'] = pd.NaT
        df['trend_score'] = pd.to_numeric(df.get('trend_score', 0.0), errors='coerce').fillna(0.0)
        df['priority_score'] = pd.to_numeric(df.get('priority_score', 0.0), errors='coerce').fillna(0.0)
        conf1 = pd.to_numeric(df['confidence_score'], errors='coerce') if 'confidence_score' in df.columns else pd.Series([None]*len(df))
        conf2 = pd.to_numeric(df['confidence'], errors='coerce') if 'confidence' in df.columns else pd.Series([None]*len(df))
        df['confidence_score'] = conf1.fillna(conf2).fillna(0.0)

        cats = sorted([c for c in df.get('category', pd.Series()).dropna().unique().tolist()]) if 'category' in df.columns else []
        langs = sorted([c for c in df.get('language', pd.Series()).dropna().unique().tolist()]) if 'language' in df.columns else []
        tones = sorted([c for c in df.get('tone', pd.Series()).dropna().unique().tolist()]) if 'tone' in df.columns else []
        sel_cat = st.sidebar.multiselect('Filter Category', cats, default=[])
        sel_lang = st.sidebar.multiselect('Filter Language', langs, default=[])
        sel_tone = st.sidebar.multiselect('Filter Tone', tones, default=[])
        df_f = df.copy()
        if len(sel_cat) > 0:
            df_f = df_f[df_f['category'].isin(sel_cat)]
        if len(sel_lang) > 0:
            df_f = df_f[df_f['language'].isin(sel_lang)]
        if len(sel_tone) > 0:
            df_f = df_f[df_f['tone'].fillna('unknown').isin(sel_tone)]
        if df['ts'].notna().any():
            min_d = df['ts'].min().date()
            max_d = df['ts'].max().date()
            date_range = st.sidebar.date_input('Filter Date Range', (min_d, max_d))
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                df_f = df_f[df_f['ts'].dt.date.between(start, end)]

        st.subheader('Overview Charts')
        cA, cB = st.columns(2)
        with cA:
            if df_f['ts'].notna().any():
                ts_df = df_f.dropna(subset=['ts']).copy()
                ts_df['date'] = ts_df['ts'].dt.date
                agg = ts_df.groupby('date', as_index=False)['trend_score'].mean()
                chart = alt.Chart(agg).mark_line(point=True).encode(x='date:T', y='trend_score:Q').properties(height=250)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info('No timestamp data available for trend over time.')
        with cB:
            tone_df = df_f.copy()
            tone_df['tone'] = tone_df.get('tone').fillna('unknown')
            tone_counts = tone_df.groupby('tone', as_index=False).size()
            chart2 = alt.Chart(tone_counts).mark_bar().encode(x='tone:N', y='size:Q').properties(height=250)
            st.altair_chart(chart2, use_container_width=True)

        st.subheader('More Charts')
        cC, cD = st.columns(2)
        with cC:
            if df_f['ts'].notna().any():
                ts_df = df_f.dropna(subset=['ts']).copy()
                ts_df['date'] = ts_df['ts'].dt.date
                agg_conf = ts_df.groupby('date', as_index=False)['confidence_score'].mean()
                chart_conf = alt.Chart(agg_conf).mark_line(point=True).encode(x='date:T', y='confidence_score:Q').properties(height=250)
                st.altair_chart(chart_conf, use_container_width=True)
            else:
                st.info('No timestamp data available for confidence over time.')
        with cD:
            tp_df = df_f.copy()
            tp_df['tone'] = tp_df.get('tone').fillna('unknown')
            agg_tp = tp_df.groupby('tone', as_index=False)['priority_score'].mean()
            chart_tp = alt.Chart(agg_tp).mark_bar().encode(x='tone:N', y='priority_score:Q').properties(height=250)
            st.altair_chart(chart_tp, use_container_width=True)

        st.subheader('Scatter: Priority vs Trend by Tone')
        scat_df = df_f.copy()
        scat_df['tone'] = scat_df.get('tone').fillna('unknown')
        chart_scat = alt.Chart(scat_df).mark_circle(size=80).encode(
            x=alt.X('priority_score:Q', title='Priority Score'),
            y=alt.Y('trend_score:Q', title='Trend Score'),
            color=alt.Color('tone:N', legend=alt.Legend(title='Tone')),
            tooltip=['title:N','priority_score:Q','trend_score:Q','tone:N']
        ).properties(height=300)
        st.altair_chart(chart_scat, use_container_width=True)

        st.subheader(sample.get('id'))
        st.text_area('Script', sample.get('script',''), height=180)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Tone', sample.get('tone'))
        c2.metric('Confidence', f"{sample.get('confidence_score', 0.0)}")
        c3.metric('Priority', f"{sample.get('priority_score', 0.0)}")
        c4.metric('Trend', f"{sample.get('trend_score', 0.0)}")
        st.metric('RL Reward', f"{sample.get('rl_reward_score', 0.0)}")
        audio_bytes = read_audio_bytes(sample.get('audio_path')) or get_or_synthesize_audio(sample)
        if audio_bytes:
            st.audio(audio_bytes, format='audio/wav')
        else:
            st.info('No audio available for sample.')