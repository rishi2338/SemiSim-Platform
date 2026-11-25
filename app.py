import math
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

MATERIALS = {
    "Si": {"name":"Silicon", "formula":"Si", "Eg0":1.12, "alpha":4.73e-4, "beta":636,
           "Nc":2.8e19, "Nv":1.04e19, "mu_n":1400, "mu_p":450, "affinity":4.05,
           "density":2.33, "crystal":"Diamond cubic", "type":"Elemental",
           "applications":["Solar cells","ICs","Power devices"]},
    "Ge": {"name":"Germanium", "formula":"Ge", "Eg0":0.66, "alpha":4.77e-4, "beta":235,
           "Nc":1.04e19, "Nv":6.0e18, "mu_n":3900, "mu_p":1900, "affinity":4.0,
           "density":5.32, "crystal":"Diamond cubic", "type":"Elemental",
           "applications":["High-speed devices","IR detectors"]},
    "GaAs": {"name":"Gallium Arsenide", "formula":"GaAs", "Eg0":1.52, "alpha":5.41e-4, "beta":204,
             "Nc":4.7e17, "Nv":7.0e18, "mu_n":8500, "mu_p":400, "affinity":4.07,
             "density":5.32, "crystal":"Zincblende", "type":"III-V Compound",
             "applications":["LEDs","Lasers","High-frequency","Solar cells"]},
    "GaN": {"name":"Gallium Nitride", "formula":"GaN", "Eg0":3.4, "alpha":7.7e-4, "beta":600,
            "Nc":2.3e18, "Nv":4.6e19, "mu_n":1000, "mu_p":200, "affinity":4.1,
            "density":6.15, "crystal":"Wurtzite", "type":"III-V Compound",
            "applications":["Blue LEDs","Power electronics","RF"]},
    "ZnO": {"name":"Zinc Oxide", "formula":"ZnO", "Eg0":3.37, "alpha":8.0e-4, "beta":700,
            "Nc":3.7e18, "Nv":1.8e19, "mu_n":200, "mu_p":5, "affinity":4.35,
            "density":5.61, "crystal":"Wurtzite", "type":"II-VI Compound",
            "applications":["UV LEDs","Transparent electronics","Sensors"]},
}
K_B_EV = 8.617e-5
Q = 1.6e-19

def bandgap(material: str, temp_c: float) -> float:
    m = MATERIALS[material]
    temp_k = temp_c + 273.15
    return m["Eg0"] - (m["alpha"] * temp_k**2) / (temp_k + m["beta"])

def intrinsic_carrier(material: str, temp_c: float) -> float:
    m = MATERIALS[material]
    temp_k = temp_c + 273.15
    eg = bandgap(material, temp_c)
    return math.sqrt(m["Nc"] * m["Nv"]) * math.exp(-eg / (2 * K_B_EV * temp_k))

def conductivity(material: str, temp_c: float, doping_log10: float, light: float = 0.0):
    m = MATERIALS[material]
    ni = intrinsic_carrier(material, temp_c)
    nd = 10 ** doping_log10
    if nd > ni:
        n, p = nd, ni**2 / nd
        carrier_type = "n-type"
    else:
        n = p = ni
        carrier_type = "intrinsic"
    generation = light * 1e16
    n += generation * 1e-6
    p += generation * 1e-6
    sigma = Q * (n * m["mu_n"] + p * m["mu_p"])
    return {"n":n, "p":p, "sigma":sigma, "type":carrier_type}

def optimization_scores(application: str):
    weights = {
        "Solar Cells":{"Eg":.4,"mu_n":.3,"affinity":.2,"density":.1},
        "LEDs":{"Eg":.5,"mu_n":.2,"affinity":.2,"crystal":.1},
        "Photodetectors":{"Eg":.3,"mu_n":.4,"mu_p":.2,"affinity":.1},
        "Power Electronics":{"Eg":.4,"mu_n":.3,"density":.3},
        "High-Frequency Devices":{"mu_n":.6,"Eg":.2,"affinity":.2},
    }[application]
    rows=[]
    for key,m in MATERIALS.items():
        score=0.0
        if weights.get("Eg"):
            score += weights["Eg"] * (max(0,1.5-abs(m["Eg0"]-1.4)) if application=="Solar Cells" else m["Eg0"]/3.5)
        if weights.get("mu_n"): score += weights["mu_n"] * min(m["mu_n"]/10000,1)
        if weights.get("mu_p"): score += weights["mu_p"] * min(m["mu_p"]/2000,1)
        if weights.get("affinity"): score += weights["affinity"] * (1-abs(m["affinity"]-4.1)/1)
        score=max(0,min(1,score))
        rows.append({"Material":m["name"],"Formula":m["formula"],"Suitability (%)":round(score*100),
                     "Applications":", ".join(m["applications"])})
    return pd.DataFrame(rows).sort_values("Suitability (%)",ascending=False).reset_index(drop=True)

def make_pdf(result, student, experiment, notes):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return None
    buffer=BytesIO()
    pdf=canvas.Canvas(buffer,pagesize=A4)
    width,height=A4
    y=height-55
    pdf.setFont("Helvetica-Bold",18); pdf.drawString(48,y,"SemiSim Experiment Report"); y-=35
    pdf.setFont("Helvetica",11)
    lines=[
        f"Student: {student or 'Student'}", f"Experiment: {experiment}",
        f"Date: {date.today().isoformat()}", "Course: Engineering Chemistry",
        "", "SIMULATION RESULTS", f"Material: {result['name']} ({result['formula']})",
        f"Temperature: {result['temperature']} deg C",
        f"Doping (log10): {result['doping']}",
        f"Bandgap: {result['Eg']:.4f} eV",
        f"Intrinsic carrier concentration: {result['ni']:.4e} cm^-3",
        f"Conductivity: {result['sigma']:.4e} S/cm",
        f"Carrier type: {result['type']}", "", "OBSERVATIONS"
    ]
    for line in lines:
        if y<70: pdf.showPage(); y=height-55; pdf.setFont("Helvetica",11)
        if line=="SIMULATION RESULTS" or line=="OBSERVATIONS":
            pdf.setFont("Helvetica-Bold",12)
        pdf.drawString(48,y,line[:105]); y-=19
        pdf.setFont("Helvetica",11)
    for paragraph in (notes or "").splitlines():
        if y<70: pdf.showPage(); y=height-55
        pdf.drawString(48,y,paragraph[:105]); y-=16
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()

st.set_page_config(page_title="SemiSim | Semiconductor Simulation",page_icon="⚛️",layout="wide")
st.markdown("""
<style>
.block-container{padding-top:2rem;padding-bottom:3rem;max-width:1450px}
.hero{padding:1.7rem 1.9rem;border-radius:18px;background:linear-gradient(120deg,#10233f,#234d78);color:white;margin-bottom:1rem}
.hero h1{color:white;margin:0;font-size:2.25rem}.hero p{color:#d9e8f8;margin:.5rem 0 0}
div[data-testid="stMetric"]{background:rgba(120,150,190,.09);padding:15px;border-radius:14px;border:1px solid rgba(120,150,190,.2)}
</style>
<div class="hero"><h1>⚛️ SemiSim</h1><p>Semiconductor material exploration, physics-based simulation, visualization and material selection</p></div>
""",unsafe_allow_html=True)

tabs=st.tabs(["Overview","Material Explorer","Simulation","Visualizations","Material Optimization","Experiment Report"])
with tabs[0]:
    st.subheader("Welcome to SemiSim")
    st.write("Explore semiconductor properties and study how temperature, doping and illumination influence carrier concentration and electrical conductivity.")
    c1,c2,c3=st.columns(3)
    c1.metric("Materials",len(MATERIALS))
    c2.metric("Simulation model","Varshni + carrier model")
    c3.metric("Core outputs","Eg · ni · σ")
    st.markdown("**Platform modules**")
    st.markdown("- Material Explorer — inspect semiconductor properties and applications.\n- Simulation Engine — calculate bandgap, intrinsic carrier concentration and conductivity.\n- Visualization Studio — compare temperature and doping responses.\n- Material Optimization — rank materials for selected device applications.\n- Experiment Report — export the latest simulation as a PDF.")
    st.info("The calculations reproduce the simplified equations and material constants supplied in the original SemiSim web application.")

with tabs[1]:
    st.subheader("Semiconductor Material Explorer")
    chosen=st.selectbox("Select a material",list(MATERIALS),format_func=lambda k:f"{MATERIALS[k]['name']} ({k})",key="explore_material")
    m=MATERIALS[chosen]
    st.markdown(f"### {m['name']}  ·  `{m['formula']}`")
    st.caption(f"{m['type']} | {m['crystal']} crystal structure")
    cols=st.columns(4)
    props=[("Bandgap at 0 K",f"{m['Eg0']:.2f} eV"),("Electron mobility",f"{m['mu_n']} cm²/V·s"),
           ("Hole mobility",f"{m['mu_p']} cm²/V·s"),("Electron affinity",f"{m['affinity']:.2f} eV"),
           ("Density",f"{m['density']:.2f} g/cm³"),("Effective density Nc",f"{m['Nc']:.2e} cm⁻³"),
           ("Effective density Nv",f"{m['Nv']:.2e} cm⁻³"),("Crystal structure",m["crystal"])]
    for i,(label,value) in enumerate(props): cols[i%4].metric(label,value)
    st.markdown("**Applications**")
    st.write(", ".join(m["applications"]))
    if st.button("Use this material in Simulation",key="use_material"):
        st.session_state["sim_material"]=chosen
        st.success("Material selected. Open the Simulation tab.")

with tabs[2]:
    st.subheader("Simulation Parameters")
    a,b=st.columns([1,1])
    with a:
        material=st.selectbox("Semiconductor material",list(MATERIALS),
            format_func=lambda k:f"{MATERIALS[k]['name']} ({k})",
            index=list(MATERIALS).index(st.session_state.get("sim_material","Si")),key="sim_material")
        temp=st.slider("Temperature (°C)",-20,150,25,1)
        doping=st.slider("Doping concentration (log₁₀ cm⁻³)",13.0,19.0,15.0,.1)
        light=st.slider("Relative illumination",0.0,100.0,0.0,1.0)
        st.caption("Voltage is retained from the source interface but is not used by its conductivity equation.")
        voltage=st.slider("Voltage (V)",0.0,5.0,.5,.1)
    with b:
        st.markdown("#### Quick simulation")
        quick_mat=st.selectbox("Quick material",list(MATERIALS),format_func=lambda k:MATERIALS[k]["name"],key="quick_mat")
        quick_temp=st.slider("Quick temperature (°C)",-20,150,25,key="quick_temp")
        q_eg=bandgap(quick_mat,quick_temp); q_ni=intrinsic_carrier(quick_mat,quick_temp)
        st.metric("Quick bandgap",f"{q_eg:.4f} eV")
        st.metric("Quick intrinsic concentration",f"{q_ni:.3e} cm⁻³")
    cond=conductivity(material,temp,doping,light)
    eg=bandgap(material,temp); ni=intrinsic_carrier(material,temp)
    result={"material":material,"name":MATERIALS[material]["name"],"formula":MATERIALS[material]["formula"],
            "temperature":temp,"doping":doping,"light":light,"voltage":voltage,"Eg":eg,"ni":ni,**cond}
    st.session_state["last_result"]=result
    st.markdown("#### Simulation Results")
    r1,r2,r3,r4=st.columns(4)
    r1.metric("Bandgap (Eg)",f"{eg:.4f} eV")
    r2.metric("Intrinsic carriers (ni)",f"{ni:.3e} cm⁻³")
    r3.metric("Conductivity (σ)",f"{cond['sigma']:.3e} S/cm")
    r4.metric("Carrier type",cond["type"])
    st.caption(f"Electron concentration n = {cond['n']:.3e} cm⁻³  |  Hole concentration p = {cond['p']:.3e} cm⁻³")
    st.success("Results update automatically when a parameter changes.")

with tabs[3]:
    st.subheader("Visualization Studio")
    mat=st.selectbox("Material for graphs",list(MATERIALS),format_func=lambda k:MATERIALS[k]["name"],key="viz_mat")
    temps=list(range(-20,151,10))
    temp_df=pd.DataFrame({"Temperature (°C)":temps,
        "Conductivity (S/cm)":[conductivity(mat,t,15,0)["sigma"] for t in temps]})
    st.markdown("#### Conductivity vs Temperature")
    st.line_chart(temp_df.set_index("Temperature (°C)"))
    dopings=[13+i*.5 for i in range(13)]
    dop_df=pd.DataFrame({"Doping (log₁₀ cm⁻³)":dopings,
        "Electron concentration (cm⁻³)":[conductivity(mat,25,d,0)["n"] for d in dopings]})
    st.markdown("#### Carrier Concentration vs Doping")
    st.line_chart(dop_df.set_index("Doping (log₁₀ cm⁻³)"))
    current=st.session_state.get("last_result")
    if current:
        st.markdown("#### Energy Band Diagram")
        gap=current["Eg"]
        band_df=pd.DataFrame({"Band":["Conduction band edge","Valence band edge"],"Energy (eV)":[gap,0]})
        st.bar_chart(band_df.set_index("Band"))
        st.caption(f"Illustrative energy separation: Eg = {gap:.4f} eV. The source application displays a schematic band diagram, not a calibrated density-of-states plot.")
        st.markdown("#### Current Parameter Response")
        st.bar_chart(pd.DataFrame({"Value":[current["Eg"],math.log10(max(current["ni"],1e-300)),math.log10(max(current["sigma"],1e-300))]},
                                  index=["Eg (eV)","log10(ni)","log10(σ)"]))

with tabs[4]:
    st.subheader("Material Optimization Workspace")
    application=st.selectbox("Target device application",["Solar Cells","LEDs","Photodetectors","Power Electronics","High-Frequency Devices"])
    ranking=optimization_scores(application)
    st.write(f"Suitability ranking for **{application}** (heuristic score based on the original platform's weights).")
    st.dataframe(ranking,hide_index=True,use_container_width=True)
    st.bar_chart(ranking.set_index("Material")[["Suitability (%)"]])
    st.caption("Scores are comparative heuristic rankings from the original SemiSim formula, not experimentally validated device-performance predictions.")

with tabs[5]:
    st.subheader("Experiment Report Generator")
    last=st.session_state.get("last_result")
    if last:
        st.write(f"Latest simulation: **{last['name']}** at **{last['temperature']} °C**")
        st.json({k:last[k] for k in ["formula","temperature","doping","Eg","ni","sigma","type"]})
        student=st.text_input("Student name")
        experiment=st.text_input("Experiment title",value="Semiconductor Bandgap and Conductivity Simulation")
        notes=st.text_area("Observations / notes")
        pdf=make_pdf(last,student,experiment,notes)
        if pdf:
            st.download_button("Download experiment report (PDF)",pdf,file_name="SemiSim_Experiment_Report.pdf",mime="application/pdf")
        else:
            st.warning("Install reportlab to enable PDF export: pip install reportlab")
    else:
        st.info("Run a simulation first to generate a report.")
st.divider()
st.caption("SemiSim Python edition · Streamlit · Educational simulation based on the supplied source project")
