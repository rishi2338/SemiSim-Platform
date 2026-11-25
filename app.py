import math
from datetime import date
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

MATERIALS = {
    "Si": {"name":"Silicon", "formula":"Si", "Eg0":1.12, "alpha":4.73e-4, "beta":636, "Nc":2.8e19, "Nv":1.04e19, "mu_n":1400, "mu_p":450, "affinity":4.05, "density":2.33, "crystal":"Diamond cubic", "type":"Elemental", "applications":["Solar cells","ICs","Power devices"]},
    "Ge": {"name":"Germanium", "formula":"Ge", "Eg0":0.66, "alpha":4.77e-4, "beta":235, "Nc":1.04e19, "Nv":6.0e18, "mu_n":3900, "mu_p":1900, "affinity":4.0, "density":5.32, "crystal":"Diamond cubic", "type":"Elemental", "applications":["High-speed devices","IR detectors"]},
    "GaAs": {"name":"Gallium Arsenide", "formula":"GaAs", "Eg0":1.52, "alpha":5.41e-4, "beta":204, "Nc":4.7e17, "Nv":7.0e18, "mu_n":8500, "mu_p":400, "affinity":4.07, "density":5.32, "crystal":"Zincblende", "type":"III-V Compound", "applications":["LEDs","Lasers","High-frequency","Solar cells"]},
    "GaN": {"name":"Gallium Nitride", "formula":"GaN", "Eg0":3.4, "alpha":7.7e-4, "beta":600, "Nc":2.3e18, "Nv":4.6e19, "mu_n":1000, "mu_p":200, "affinity":4.1, "density":6.15, "crystal":"Wurtzite", "type":"III-V Compound", "applications":["Blue LEDs","Power electronics","RF"]},
    "ZnO": {"name":"Zinc Oxide", "formula":"ZnO", "Eg0":3.37, "alpha":8.0e-4, "beta":700, "Nc":3.7e18, "Nv":1.8e19, "mu_n":200, "mu_p":5, "affinity":4.35, "density":5.61, "crystal":"Wurtzite", "type":"II-VI Compound", "applications":["UV LEDs","Transparent electronics","Sensors"]},
}
K_B_EV = 8.617e-5
Q = 1.6e-19

st.set_page_config(page_title="SemiSim | Semiconductor Lab", page_icon="⚛️", layout="wide", initial_sidebar_state="expanded")

def bandgap(material, temp_c):
    m = MATERIALS[material]
    tk = temp_c + 273.15
    return m["Eg0"] - (m["alpha"] * tk**2) / (tk + m["beta"])

def intrinsic_carrier(material, temp_c):
    m = MATERIALS[material]
    tk = temp_c + 273.15
    eg = bandgap(material, temp_c)
    return math.sqrt(m["Nc"] * m["Nv"]) * math.exp(-eg / (2 * K_B_EV * tk))

def conductivity(material, temp_c, doping_log10, light=0.0):
    m = MATERIALS[material]
    ni = intrinsic_carrier(material, temp_c)
    nd = 10 ** doping_log10
    if nd > ni:
        n, p, carrier_type = nd, ni**2 / nd, "n-type"
    else:
        n, p, carrier_type = ni, ni, "intrinsic"
    generation = light * 1e16
    n += generation * 1e-6
    p += generation * 1e-6
    return {"n":n, "p":p, "sigma":Q * (n*m["mu_n"] + p*m["mu_p"]), "type":carrier_type}

def optimization_scores(application):
    weights = {
        "Solar Cells":{"Eg":.4,"mu_n":.3,"affinity":.2},
        "LEDs":{"Eg":.5,"mu_n":.2,"affinity":.2},
        "Photodetectors":{"Eg":.3,"mu_n":.4,"mu_p":.2,"affinity":.1},
        "Power Electronics":{"Eg":.4,"mu_n":.3},
        "High-Frequency Devices":{"mu_n":.6,"Eg":.2,"affinity":.2},
    }[application]
    rows=[]
    for _,m in MATERIALS.items():
        score=0.0
        if weights.get("Eg"): score += weights["Eg"] * (max(0,1.5-abs(m["Eg0"]-1.4)) if application=="Solar Cells" else m["Eg0"]/3.5)
        if weights.get("mu_n"): score += weights["mu_n"] * min(m["mu_n"]/10000,1)
        if weights.get("mu_p"): score += weights["mu_p"] * min(m["mu_p"]/2000,1)
        if weights.get("affinity"): score += weights["affinity"] * (1-abs(m["affinity"]-4.1))
        rows.append({"Material":m["name"],"Formula":m["formula"],"Suitability (%)":round(max(0,min(1,score))*100),"Applications":", ".join(m["applications"])})
    return pd.DataFrame(rows).sort_values("Suitability (%)",ascending=False).reset_index(drop=True)

def crystal_figure(material):
    # A clean schematic two-species cubic unit cell. It is an interactive teaching
    # visual, not an atomically exact crystallographic refinement.
    coords=[]
    for x in range(3):
        for y in range(3):
            for z in range(3):
                if (x+y+z) % 2 == 0:
                    coords.append((x,y,z,0))
                else:
                    coords.append((x,y,z,1))
    edges=[]
    for i,a in enumerate(coords):
        for j,b in enumerate(coords):
            if j <= i: continue
            d=sum((a[k]-b[k])**2 for k in range(3))
            if d == 1:
                edges.append((a,b))
    ex,ey,ez=[],[],[]
    for a,b in edges:
        ex += [a[0],b[0],None]; ey += [a[1],b[1],None]; ez += [a[2],b[2],None]
    fig=go.Figure()
    fig.add_trace(go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",line=dict(color="rgba(120,170,210,.32)",width=4),hoverinfo="skip",showlegend=False))
    for species,color,label in [(0,"#61D9FF","Atom A"),(1,"#B49AFF","Atom B")]:
        pts=[p for p in coords if p[3]==species]
        fig.add_trace(go.Scatter3d(x=[p[0] for p in pts],y=[p[1] for p in pts],z=[p[2] for p in pts],
            mode="markers",name=label,marker=dict(size=10,color=color,opacity=.96,line=dict(color="white",width=1)),
            hovertemplate="x=%{x}, y=%{y}, z=%{z}<extra>"+label+"</extra>"))
    fig.update_layout(template="plotly_dark",height=410,margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",y=1.02,x=0.02),
        scene=dict(bgcolor="rgba(0,0,0,0)",xaxis=dict(visible=False),yaxis=dict(visible=False),zaxis=dict(visible=False),
                   aspectmode="cube",camera=dict(eye=dict(x=1.65,y=1.55,z=1.35))))
    return fig

def chart_layout(fig, height=360):
    fig.update_layout(template="plotly_dark",height=height,margin=dict(l=12,r=12,t=38,b=12),
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif",color="#C7D3E2"),
        xaxis=dict(showgrid=False,zeroline=False),yaxis=dict(gridcolor="rgba(150,175,210,.12)",zeroline=False),
        hoverlabel=dict(bgcolor="#101C2B",font_color="#F3F7FC"))
    return fig

def make_pdf(result, student, experiment, notes):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return None
    buffer=BytesIO(); pdf=canvas.Canvas(buffer,pagesize=A4); _,height=A4; y=height-55
    pdf.setFont("Helvetica-Bold",18); pdf.drawString(48,y,"SemiSim Experiment Report"); y-=35
    pdf.setFont("Helvetica",11)
    lines=[f"Student: {student or 'Student'}",f"Experiment: {experiment}",f"Date: {date.today().isoformat()}",
           "","SIMULATION RESULTS",f"Material: {result['name']} ({result['formula']})",
           f"Temperature: {result['temperature']} deg C",f"Doping (log10): {result['doping']}",
           f"Bandgap: {result['Eg']:.4f} eV",f"Intrinsic carrier concentration: {result['ni']:.4e} cm^-3",
           f"Conductivity: {result['sigma']:.4e} S/cm",f"Carrier type: {result['type']}","","OBSERVATIONS"]
    for line in lines+(notes or "").splitlines():
        if y<70: pdf.showPage(); y=height-55; pdf.setFont("Helvetica",11)
        if line in ("SIMULATION RESULTS","OBSERVATIONS"): pdf.setFont("Helvetica-Bold",12)
        pdf.drawString(48,y,line[:105]); y-=19; pdf.setFont("Helvetica",11)
    pdf.save(); buffer.seek(0); return buffer.getvalue()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--ink:#eaf2ff;--muted:#8ea3bd;--cyan:#55d9f5;--violet:#a78bfa;--line:rgba(139,174,215,.15)}
html,body,[class*="css"]{font-family:'Manrope',sans-serif}
.stApp{background:radial-gradient(ellipse at 10% 0%,rgba(29,100,160,.22),transparent 34%),radial-gradient(ellipse at 92% 12%,rgba(115,73,190,.17),transparent 30%),#07111f;color:var(--ink)}
[data-testid="stHeader"]{background:rgba(7,17,31,.72);backdrop-filter:blur(16px)}
.block-container{max-width:1500px;padding-top:1.5rem;padding-bottom:3.2rem}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0b192a,#091321);border-right:1px solid var(--line)}
section[data-testid="stSidebar"] *{color:#dce9f8}
.hero{position:relative;overflow:hidden;padding:30px 34px;border:1px solid rgba(110,190,235,.24);border-radius:24px;background:linear-gradient(112deg,rgba(14,38,63,.97),rgba(22,35,69,.9) 60%,rgba(58,39,93,.78));box-shadow:0 24px 80px rgba(0,0,0,.24);margin:8px 0 24px;animation:rise .75s ease both}
.hero:before{content:'';position:absolute;width:360px;height:360px;right:4%;top:-210px;border-radius:50%;background:rgba(65,209,246,.24);filter:blur(55px);animation:pulse 6s ease-in-out infinite}
.hero:after{content:'';position:absolute;width:180px;height:180px;right:20%;bottom:-140px;border-radius:50%;background:rgba(160,119,255,.3);filter:blur(35px)}
.eyebrow{font:500 11px 'DM Mono',monospace;letter-spacing:3px;color:#72dff8;text-transform:uppercase}
.hero h1{font-size:clamp(36px,5vw,58px);font-weight:800;letter-spacing:-2.5px;margin:9px 0 4px;color:#f5f9ff}
.hero p{color:#afc3db;font-size:15px;max-width:650px;margin:0}
.hero-tag{display:inline-block;margin-top:20px;padding:7px 11px;border:1px solid rgba(116,220,248,.28);border-radius:30px;color:#aeeeff;font:11px 'DM Mono',monospace;background:rgba(53,168,205,.08)}
.section-kicker{font:500 10px 'DM Mono',monospace;letter-spacing:2px;color:#69d8f2;text-transform:uppercase;margin:10px 0 6px}
.panel{background:linear-gradient(145deg,rgba(18,35,55,.88),rgba(11,24,40,.86));border:1px solid var(--line);border-radius:18px;padding:18px 20px;box-shadow:0 12px 38px rgba(0,0,0,.13);transition:transform .25s ease,border-color .25s ease}
.panel:hover{transform:translateY(-3px);border-color:rgba(91,213,245,.35)}
.metric-label{font-size:11px;color:#8ea7c2;text-transform:uppercase;letter-spacing:1.3px}
.metric-value{font-size:25px;font-weight:800;color:#f0f7ff;margin-top:5px;letter-spacing:-.7px}
.metric-foot{font:10px 'DM Mono',monospace;color:#68d8f1;margin-top:3px}
div[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(18,39,61,.9),rgba(11,25,42,.9));border:1px solid var(--line);padding:16px 18px;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.12)}
div[data-testid="stMetric"] label{color:#91a9c4}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#f2f7ff}
.stTabs [data-baseweb="tab-list"]{gap:7px;background:rgba(12,26,43,.78);padding:7px;border:1px solid var(--line);border-radius:15px}
.stTabs [data-baseweb="tab"]{height:42px;border-radius:10px;color:#9bb0c9;font-weight:700}
.stTabs [aria-selected="true"]{background:linear-gradient(100deg,rgba(48,157,190,.25),rgba(133,99,220,.22));color:#effaff}
.stButton>button,.stDownloadButton>button{border:1px solid rgba(86,212,241,.4);border-radius:11px;background:linear-gradient(110deg,#126b8d,#51418c);color:white;font-weight:700;transition:all .2s ease}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);border-color:#70e5ff;box-shadow:0 8px 25px rgba(39,171,208,.2);color:white}
.stSelectbox>div>div,.stTextInput input,.stTextArea textarea{background:#101f32!important;border-color:var(--line)!important;border-radius:10px!important}
div[data-testid="stSlider"] [data-testid="stThumbValue"]{color:#72def7}
hr{border-color:var(--line)}
footer{visibility:hidden}
@keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{transform:scale(.92);opacity:.6}50%{transform:scale(1.12);opacity:1}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
<div class="hero">
  <div class="eyebrow">Semiconductor physics · interactive laboratory</div>
  <h1>SEMI<span style="color:#62dcf5">SIM</span></h1>
  <p>Explore material properties, simulate charge transport and visualize semiconductor behaviour in an interactive digital lab.</p>
  <div class="hero-tag">● LIVE SIMULATION ENVIRONMENT &nbsp; / &nbsp; PYTHON + STREAMLIT</div>
</div>
""",unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚛️ SemiSim")
    st.caption("SEMICONDUCTOR LAB / 01")
    page=st.radio("WORKSPACE",["Overview","Material Explorer","Simulation Lab","3D Crystal Model","Analytics","Material Optimizer","Lab Report"],label_visibility="visible")
    st.divider()
    st.markdown("**MATERIAL DATABASE**")
    st.caption("05 semiconductor materials")
    st.caption("Varshni · Carrier transport · Conductivity")
    st.markdown("---")
    st.caption("Educational model · v2.0")

def section(title, subtitle):
    st.markdown(f'<div class="section-kicker">SEMI SIM / WORKSPACE</div><h2 style="letter-spacing:-1px;margin:0 0 4px">{title}</h2><p style="color:#8ea3bd;margin:0 0 22px">{subtitle}</p>',unsafe_allow_html=True)

def metric_card(label,value,foot):
    st.markdown(f'<div class="panel"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-foot">{foot}</div></div>',unsafe_allow_html=True)

if page=="Overview":
    section("Semiconductor command center","A live overview of the material library and simulation capabilities.")
    a,b,c=st.columns(3)
    with a: metric_card("Material library","05","ELEMENTAL + COMPOUND")
    with b: metric_card("Physics engine","3 MODELS","BANDGAP · CARRIERS · CONDUCTIVITY")
    with c: metric_card("Visualization","3D + 2D","INTERACTIVE PLOTS")
    st.write("")
    left,right=st.columns([1.25,1])
    with left:
        st.markdown('<div class="panel"><div class="section-kicker">LAB OVERVIEW</div><h3>From material to measurable behaviour</h3><p style="color:#9bb0c8">Change temperature, doping and illumination to explore how semiconductor properties respond. Every simulation result is calculated from the selected material parameters.</p></div>',unsafe_allow_html=True)
        st.markdown("#### Explore the workspace")
        st.markdown("- **Material Explorer** — compare physical and electrical properties.\n- **Simulation Lab** — calculate bandgap, carrier density and conductivity.\n- **3D Crystal Model** — rotate and inspect a schematic atomic lattice.\n- **Analytics** — explore temperature and doping response curves.\n- **Material Optimizer** — compare materials for device applications.")
    with right:
        st.markdown("#### Material quick view")
        for key,m in MATERIALS.items():
            st.markdown(f'<div class="panel" style="padding:11px 15px;margin-bottom:9px"><span style="color:#6edcf5;font-weight:800">{key}</span> &nbsp; <b>{m["name"]}</b><span style="float:right;color:#9bb0c8;font:11px DM Mono">{m["Eg0"]:.2f} eV</span><div style="font-size:11px;color:#8098b3">{m["crystal"]} · {m["type"]}</div></div>',unsafe_allow_html=True)

elif page=="Material Explorer":
    section("Material explorer","Select a semiconductor to inspect its physical properties and common applications.")
    chosen=st.selectbox("SELECT MATERIAL",list(MATERIALS),format_func=lambda k:f'{MATERIALS[k]["name"]}  ·  {k}')
    m=MATERIALS[chosen]
    st.markdown(f'<div class="panel"><div class="section-kicker">{m["type"]} / {m["crystal"]}</div><h1 style="font-size:38px;margin:0">{m["name"]} <span style="color:#61d9f5">{m["formula"]}</span></h1><p style="color:#91a9c4">Semiconductor material profile</p></div>',unsafe_allow_html=True)
    st.write("")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Bandgap at 0 K",f'{m["Eg0"]:.2f} eV')
    c2.metric("Electron mobility",f'{m["mu_n"]:,} cm²/V·s')
    c3.metric("Hole mobility",f'{m["mu_p"]:,} cm²/V·s')
    c4.metric("Electron affinity",f'{m["affinity"]:.2f} eV')
    c5,c6,c7,c8=st.columns(4)
    c5.metric("Density",f'{m["density"]:.2f} g/cm³')
    c6.metric("Effective Nc",f'{m["Nc"]:.2e}')
    c7.metric("Effective Nv",f'{m["Nv"]:.2e}')
    c8.metric("Crystal structure",m["crystal"])
    st.markdown("#### Typical applications")
    st.write("  ·  ".join(m["applications"]))
    st.plotly_chart(crystal_figure(chosen),use_container_width=True,config={"displaylogo":False,"scrollZoom":True})

elif page=="Simulation Lab":
    section("Simulation lab","Adjust the experimental conditions and observe calculated semiconductor responses.")
    with st.container(border=True):
        col1,col2=st.columns([1,1.2])
        with col1:
            material=st.selectbox("SEMICONDUCTOR",list(MATERIALS),format_func=lambda k:f'{MATERIALS[k]["name"]} ({k})',key="lab_material")
            temp=st.slider("Temperature (°C)",-20,150,25,1)
            doping=st.slider("Doping concentration · log₁₀ cm⁻³",13.0,19.0,15.0,.1)
            light=st.slider("Relative illumination",0.0,100.0,0.0,1.0)
            voltage=st.slider("Voltage (V)",0.0,5.0,.5,.1)
            st.caption("Voltage is displayed for experimental context; the original conductivity equation does not use voltage.")
        with col2:
            m=MATERIALS[material]; eg=bandgap(material,temp); ni=intrinsic_carrier(material,temp); cond=conductivity(material,temp,doping,light)
            st.markdown("#### Computed output")
            k1,k2=st.columns(2)
            k1.metric("Bandgap · Eg",f"{eg:.4f} eV")
            k2.metric("Intrinsic carriers · ni",f"{ni:.3e} cm⁻³")
            k3,k4=st.columns(2)
            k3.metric("Conductivity · σ",f'{cond["sigma"]:.3e} S/cm')
            k4.metric("Carrier regime",cond["type"])
            st.markdown(f'<div class="panel"><div class="metric-label">CHARGE CARRIER DENSITY</div><div style="display:flex;justify-content:space-between;margin-top:12px"><span style="color:#62d9f5">Electrons (n)</span><b>{cond["n"]:.3e} cm⁻³</b></div><div style="height:7px;border-radius:8px;background:linear-gradient(90deg,#53d5f2 0%,#53d5f2 65%,#293a50 65%);margin:9px 0 13px"></div><div style="display:flex;justify-content:space-between"><span style="color:#b69aff">Holes (p)</span><b>{cond["p"]:.3e} cm⁻³</b></div></div>',unsafe_allow_html=True)
    result={"material":material,"name":MATERIALS[material]["name"],"formula":MATERIALS[material]["formula"],"temperature":temp,"doping":doping,"light":light,"voltage":voltage,"Eg":eg,"ni":ni,**cond}
    st.session_state["last_result"]=result
    st.markdown("#### Bandgap response at selected temperature")
    t_range=list(range(-20,151,5))
    fig=go.Figure(go.Scatter(x=t_range,y=[bandgap(material,t) for t in t_range],mode="lines",name="Bandgap",
        line=dict(color="#5bdcf5",width=3),fill="tozeroy",fillcolor="rgba(76,199,235,.10)"))
    fig.add_vline(x=temp,line_dash="dot",line_color="#b49aff",annotation_text="Selected temperature")
    fig.update_layout(title="Varshni bandgap model",xaxis_title="Temperature (°C)",yaxis_title="Bandgap (eV)")
    st.plotly_chart(chart_layout(fig),use_container_width=True,config={"displaylogo":False})

elif page=="3D Crystal Model":
    section("3D crystal laboratory","Explore an interactive schematic unit cell. Drag to rotate, scroll to zoom and hover over atoms.")
    material=st.selectbox("SELECT MATERIAL",list(MATERIALS),format_func=lambda k:f'{MATERIALS[k]["name"]} · {MATERIALS[k]["crystal"]}',key="crystal_material")
    m=MATERIALS[material]
    st.markdown(f'<div class="panel"><div class="section-kicker">INTERACTIVE ATOMIC LATTICE</div><h2 style="margin:0">{m["name"]} <span style="color:#62d9f5">{m["formula"]}</span></h2><p style="color:#91a9c4;margin:3px 0">Structure family: {m["crystal"]} · Two-species schematic view</p></div>',unsafe_allow_html=True)
    st.plotly_chart(crystal_figure(material),use_container_width=True,config={"displaylogo":False,"scrollZoom":True,"responsive":True})
    a,b=st.columns(2)
    with a: metric_card("Crystal family",m["crystal"],"MATERIAL DATABASE VALUE")
    with b: metric_card("Lattice view","INTERACTIVE 3D","ROTATE · PAN · ZOOM")
    st.info("The 3D lattice is an illustrative two-species teaching model, not an exact crystallographic unit cell or bond-length model. Use a crystallography dataset for atomically precise structures.")

elif page=="Analytics":
    section("Analytics studio","Interactive response curves for temperature, doping and material comparison.")
    mat=st.selectbox("FOCUS MATERIAL",list(MATERIALS),format_func=lambda k:MATERIALS[k]["name"],key="analytics_material")
    temps=list(range(-20,151,5))
    fig=go.Figure()
    for key in MATERIALS:
        vals=[conductivity(key,t,15)["sigma"] for t in temps]
        fig.add_trace(go.Scatter(x=temps,y=vals,mode="lines",name=key,line=dict(width=2.5 if key==mat else 1.3)))
    fig.update_layout(title="Conductivity vs temperature · all materials",xaxis_title="Temperature (°C)",yaxis_title="Conductivity (S/cm)",yaxis_type="log",legend_title="Material")
    st.plotly_chart(chart_layout(fig,420),use_container_width=True,config={"displaylogo":False})
    dops=[13+i*.25 for i in range(25)]
    fig2=go.Figure()
    for key in MATERIALS:
        vals=[conductivity(key,25,d)["n"] for d in dops]
        fig2.add_trace(go.Scatter(x=dops,y=vals,mode="lines",name=key,line=dict(width=2.5 if key==mat else 1.3)))
    fig2.update_layout(title="Electron concentration vs doping",xaxis_title="Doping · log₁₀ cm⁻³",yaxis_title="Electron concentration (cm⁻³)",yaxis_type="log")
    st.plotly_chart(chart_layout(fig2,420),use_container_width=True,config={"displaylogo":False})
    egfig=go.Figure()
    for key in MATERIALS:
        egfig.add_trace(go.Scatter(x=temps,y=[bandgap(key,t) for t in temps],mode="lines",name=key))
    egfig.update_layout(title="Bandgap vs temperature · Varshni model",xaxis_title="Temperature (°C)",yaxis_title="Bandgap (eV)")
    st.plotly_chart(chart_layout(egfig,380),use_container_width=True,config={"displaylogo":False})

elif page=="Material Optimizer":
    section("Material optimizer","Compare a heuristic material ranking for a target semiconductor application.")
    application=st.selectbox("TARGET APPLICATION",["Solar Cells","LEDs","Photodetectors","Power Electronics","High-Frequency Devices"])
    ranking=optimization_scores(application)
    fig=go.Figure(go.Bar(x=ranking["Suitability (%)"],y=ranking["Material"],orientation="h",
        marker=dict(color=ranking["Suitability (%)"],colorscale=[[0,"#435c80"],[1,"#57d8f4"]],line=dict(width=0)),
        text=ranking["Suitability (%)"].astype(str)+"%",textposition="outside"))
    fig.update_layout(title=f"Relative material score · {application}",xaxis_title="Heuristic score (%)",yaxis_title="",yaxis=dict(autorange="reversed"),xaxis=dict(range=[0,115]))
    st.plotly_chart(chart_layout(fig,380),use_container_width=True,config={"displaylogo":False})
    st.dataframe(ranking,hide_index=True,use_container_width=True)
    st.caption("Scores are heuristic comparisons based on the original platform's weighting approach. They are not experimentally validated device-performance predictions.")

elif page=="Lab Report":
    section("Experiment report","Generate a downloadable PDF from your latest simulation.")
    last=st.session_state.get("last_result")
    if last:
        st.markdown(f'**Latest run:** {last["name"]} · {last["temperature"]} °C · {last["type"]}')
        student=st.text_input("Student name")
        experiment=st.text_input("Experiment title",value="Semiconductor Bandgap and Conductivity Simulation")
        notes=st.text_area("Observations / notes")
        pdf=make_pdf(last,student,experiment,notes)
        if pdf: st.download_button("Download experiment report · PDF",pdf,file_name="SemiSim_Experiment_Report.pdf",mime="application/pdf")
        else: st.warning("Install reportlab to enable PDF export.")
    else:
        st.info("Run a simulation in the Simulation Lab first. Your latest result will appear here.")
    st.markdown("#### Report preview")
    if last: st.json({k:last[k] for k in ["formula","temperature","doping","Eg","ni","sigma","type"]})

st.markdown('<div style="margin-top:38px;padding:16px 0;border-top:1px solid rgba(139,174,215,.15);display:flex;justify-content:space-between;color:#7087a2;font:10px DM Mono;letter-spacing:1px"><span>SEMISIM / SEMICONDUCTOR DIGITAL LAB</span><span>PYTHON · STREAMLIT · PLOTLY</span></div>',unsafe_allow_html=True)
