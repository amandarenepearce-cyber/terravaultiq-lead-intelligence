import pandas as pd
import streamlit as st
from datetime import datetime
from discovery import discover_businesses, search_public_topics, expand_topic_queries
from enrichment import enrich_rows
from scoring import score_rows
from packager import build_package_summary, normalize_zip_list

st.set_page_config(page_title='Lead Intelligence Engine v3', page_icon='📈', layout='wide')
if 'results_df' not in st.session_state:
    st.session_state.results_df = pd.DataFrame()

st.title('Lead Intelligence Engine v3')
st.caption('Patched version with tighter niche filtering and cleaner search behavior.')

tab1, tab2, tab3 = st.tabs(['Search', 'Lead Package Builder', 'Search Planner'])

with tab1:
    left, right = st.columns([2, 1])
    with right:
        st.subheader('Search Options')
        scan_mode = st.radio('Scan Mode', ['Single ZIP Deep Scan', 'Multi-ZIP Area Scan'], index=0)
        search_mode = st.selectbox('Search Mode', [
            'Marketing Prospect Finder',
            'Custom Business Search',
            'Public Intent Search',
            'Relocation Interest Finder',
            'Community Interest Finder',
            'Demand Signal Scanner',
        ])
        use_google = st.checkbox('Use Google API if available', value=False)
        use_osm = st.checkbox('Use OpenStreetMap backup', value=True)
        do_enrich = st.checkbox('Find public business contact info', value=False)
        do_score = st.checkbox('Score business leads', value=False)
        top_only = st.checkbox('Top 100 only', value=True)
        public_pages_only = st.checkbox('Public pages only', value=True)
        max_pages = st.slider('Public search pages', 1, 5, 2)
        show_only_high_intent = st.checkbox('High-intent results only', value=False)

    with left:
        st.subheader('Location & Keywords')
        if scan_mode == 'Single ZIP Deep Scan':
            zip_code = st.text_input('ZIP CODE', placeholder='60614')
            zip_list_text = ''
        else:
            zip_code = ''
            zip_list_text = st.text_area('ZIP LIST', placeholder='60614, 60610, 60657')
        radius = st.number_input('RADIUS (miles)', min_value=1, max_value=100, value=25, step=1)
        area_label = st.text_input('CITY / AREA LABEL', value='', placeholder='Fayetteville NC')

        defaults = {
            'Marketing Prospect Finder': ('INDUSTRY / CATEGORY', 'roofing'),
            'Custom Business Search': ('CATEGORY / KEYWORD', 'roofing'),
            'Public Intent Search': ('TOPIC / KEYWORD', 'need a roofer'),
            'Relocation Interest Finder': ('TARGET AREA', 'moving to fayetteville nc'),
            'Community Interest Finder': ('COMMUNITY / INTEREST', 'jeep lovers'),
            'Demand Signal Scanner': ('SERVICE / DEMAND TOPIC', 'roofer'),
        }
        label, default = defaults[search_mode]
        category_or_topic = st.text_input(label, value=default)

        if search_mode in ['Public Intent Search', 'Relocation Interest Finder', 'Community Interest Finder', 'Demand Signal Scanner']:
            with st.expander('Suggested public search phrases'):
                for p in expand_topic_queries(search_mode, category_or_topic.strip(), zip_code=zip_code.strip(), area_label=area_label.strip()):
                    st.code(p, language=None)

        run_search = st.button('FIND LEADS', use_container_width=True)

    if run_search:
        try:
            zips = [zip_code.strip()] if scan_mode == 'Single ZIP Deep Scan' and zip_code.strip() else normalize_zip_list(zip_list_text) if scan_mode != 'Single ZIP Deep Scan' else []
            all_rows = []

            if search_mode in ['Marketing Prospect Finder', 'Custom Business Search']:
                if not zips:
                    st.error('Please enter at least one ZIP code for business searches.')
                else:
                    mode = 'marketing' if search_mode == 'Marketing Prospect Finder' else 'custom'
                    prog = st.progress(0, text='Searching businesses...')
                    for idx, z in enumerate(zips):
                        rows = discover_businesses(
                            z,
                            float(radius),
                            mode,
                            category_or_topic.strip(),
                            use_google,
                            use_osm or not use_google
                        )
                        for row in rows:
                            row['search_mode'] = search_mode
                            row['search_keyword'] = category_or_topic.strip()
                            row['source_zip'] = z
                        all_rows.extend(rows)
                        prog.progress((idx + 1) / len(zips), text=f'Business search {idx+1}/{len(zips)}')
                    prog.empty()

                    if do_enrich and all_rows:
                        limit = min(len(all_rows), 20)
                        st.info(f'Enriching first {limit} rows.')
                        all_rows = enrich_rows(all_rows[:limit]) + all_rows[limit:]
                    if do_score and all_rows:
                        all_rows = score_rows(all_rows)
            else:
                target_zips = zips if zips else ['']
                prog = st.progress(0, text='Searching public pages...')
                for idx, z in enumerate(target_zips):
                    rows = search_public_topics(
                        search_mode,
                        category_or_topic.strip(),
                        z,
                        area_label.strip(),
                        max_pages,
                        use_google,
                        public_pages_only,
                        show_only_high_intent
                    )
                    for row in rows:
                        row['search_mode'] = search_mode
                        row['search_keyword'] = category_or_topic.strip()
                        row['source_zip'] = z
                        row['area_label'] = area_label.strip()
                    all_rows.extend(rows)
                    prog.progress((idx + 1) / len(target_zips), text=f'Public search {idx+1}/{len(target_zips)}')
                prog.empty()

            if show_only_high_intent and all_rows and 'intent_score' in pd.DataFrame(all_rows).columns:
                all_rows = sorted(all_rows, key=lambda r: int(r.get('intent_score', 0)), reverse=True)

            if top_only and all_rows:
                if all_rows and str(all_rows[0].get('lead_score', '')).strip():
                    all_rows = sorted(all_rows, key=lambda r: int(r.get('lead_score', 0)), reverse=True)[:100]
                else:
                    all_rows = all_rows[:100]

            if not all_rows:
                st.warning('No results found.')
            else:
                df = pd.DataFrame(all_rows)
                st.session_state.results_df = df
                st.success(f'Found {len(df)} results.')
                st.dataframe(df, use_container_width=True, hide_index=True, height=520)
                st.download_button(
                    'Download Search Results CSV',
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
        except Exception as e:
            st.error(f'Error: {e}')

with tab2:
    st.subheader('Build a Lead Package')
    if st.session_state.results_df.empty:
        st.info('Run a search first in the Search tab.')
    else:
        df = st.session_state.results_df.copy()
        c1, c2, c3 = st.columns(3)
        with c1:
            package_name = st.text_input('Package Name', value='Chicago Roofing Demand Signals')
        with c2:
            seller_name = st.text_input('Prepared By', value='Amanda')
        with c3:
            max_rows = st.number_input('Max Leads in Package', min_value=10, max_value=5000, value=min(250, len(df)), step=10)
        package_df = df.head(int(max_rows)).copy()
        summary = build_package_summary(package_df, package_name, seller_name)
        st.text(summary)
        st.dataframe(package_df, use_container_width=True, hide_index=True, height=450)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button('Download Lead Package CSV', data=package_df.to_csv(index=False).encode('utf-8'), file_name=f"{package_name.lower().replace(' ','_')}.csv", mime='text/csv', use_container_width=True)
        with d2:
            st.download_button('Download Package Summary TXT', data=summary.encode('utf-8'), file_name=f"{package_name.lower().replace(' ','_')}_summary.txt", mime='text/plain', use_container_width=True)

with tab3:
    st.subheader('Search Planner')
    planner_mode = st.selectbox('Planner Mode', ['Public Intent Search', 'Relocation Interest Finder', 'Community Interest Finder', 'Demand Signal Scanner'])
    planner_topic = st.text_input('Main Keyword', value='roofer')
    planner_zip = st.text_input('ZIP', value='28303')
    planner_area = st.text_input('Area Label', value='Fayetteville NC')
    for p in expand_topic_queries(planner_mode, planner_topic.strip(), planner_zip.strip(), planner_area.strip()):
        st.code(p, language=None)

st.markdown('---')
st.caption('Use this for public business leads and public topic research only.')
