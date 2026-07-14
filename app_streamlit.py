from __future__ import annotations

from pathlib import Path

import streamlit as st

from hydride_agent.agent import run_agent

st.set_page_config(page_title="NH3 Storage Agent", layout="wide")
st.title("NH₃ Storage Agent")
st.caption(
    "Traceable analysis of reported material states, ionic conductivity, hydrogen release, and coordination hypotheses."
)

if "session_id" not in st.session_state:
    st.session_state.session_id = "streamlit-session"

question = st.text_area(
    "Question",
    value=(
        "Using the NH3 Storage dataset, compare the raw counts of solid, "
        "mixed/transition, and liquid records across material families. Highlight borohydrides."
    ),
    height=130,
)

if st.button("Run analysis", type="primary"):
    with st.spinner("Running the selected database skill..."):
        result = run_agent(question, session_id=st.session_state.session_id)
    st.markdown(result.answer)
    for file_path in result.files:
        path = Path(file_path)
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            st.image(str(path), caption=path.name)
        elif path.exists():
            st.download_button(
                label=f"Download {path.name}",
                data=path.read_bytes(),
                file_name=path.name,
            )
