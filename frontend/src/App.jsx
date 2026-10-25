import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowDownRight, BarChart3, CheckCircle2, Cloud, Cpu, Database, Leaf, LoaderCircle, MapPin, MemoryStick, RefreshCw, Server, ShieldCheck, Zap } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { calculateWorkload, getRegions, optimizeWorkload } from './services/api'

const initialForm = { provider: '', region_code: '', location: 'India', cpu_utilization: 50, ram_gb: 8, storage_gb: 100, runtime_hours: 24, vm_count: 1 }
const fmt = (value, digits = 3) => Number.isFinite(Number(value)) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : '—'

export default function App() {
  const [regionData, setRegionData] = useState({ providers: [], regions: [] })
  const [form, setForm] = useState(initialForm)
  const [result, setResult] = useState(null)
  const [optimization, setOptimization] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadRegions() {
    try {
      const data = await getRegions()
      setRegionData(data)
      const providers = data.providers || []
      const rows = data.regions || []
      if (providers.length && !form.provider) {
        const provider = providers[0]
        const region = rows.find(r => String(r.Provider).toLowerCase() === provider.toLowerCase())
        setForm(f => ({ ...f, provider, region_code: region?.Region_Code || '' }))
      }
    } catch (e) { setError(`Could not connect to the backend. Start the FastAPI server and retry. ${e.message}`) }
  }
  useEffect(() => { loadRegions() }, [])

  const providers = regionData.providers || []
  const availableRegions = useMemo(() => (regionData.regions || []).filter(r => String(r.Provider || '').toLowerCase() === form.provider.toLowerCase()), [regionData, form.provider])
  const update = (key, value) => setForm(f => ({ ...f, [key]: value }))
  const payload = () => ({
    ...form,
    cpu_utilization: Number(form.cpu_utilization), ram_gb: Number(form.ram_gb),
    storage_gb: Number(form.storage_gb), runtime_hours: Number(form.runtime_hours), vm_count: Number(form.vm_count),
  })

  async function calculate() {
    setError(''); setNotice(''); setOptimization(null); setBusy(true)
    try {
      const data = await calculateWorkload(payload())
      setResult(data)
      setNotice('Calculation completed.')
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  async function optimize() {
    setError(''); setNotice(''); setBusy(true)
    try {
      const data = await optimizeWorkload(payload())
      setOptimization(data)
      setResult(data.recommended_region)
      setNotice(`Compared ${data.regions_compared} regions for ${data.matched_location || form.location} across ${(data.providers_compared || []).join(', ') || 'available providers'}. Results are ranked by Recommendation Index.`)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const comparisons = optimization?.comparisons || []
  const chartData = comparisons.map(x => ({ name: x.region_name || x.region_code, emissions: x.carbon?.carbon_kg || 0, intensity: x.carbon_intensity_gco2e_per_kwh }))
  const selectedRegion = availableRegions.find(r => String(r.Region_Code) === String(form.region_code))

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Leaf size={22}/></div><div><strong>CarbonCloud</strong><span>OPTIMIZER</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <a className="nav-item active" href="#overview"><BarChart3 size={18}/> Overview</a>
      <a className="nav-item" href="#workload"><Zap size={18}/> Workload analysis</a>
      <a className="nav-item" href="#comparison"><MapPin size={18}/> Region optimizer</a>
      <div className="sidebar-bottom"><div className="status-dot"></div><div><b>Local environment</b><span>API-connected dashboard</span></div></div>
    </aside>
    <main className="main-content" id="overview">
      <header className="topbar"><div><div className="eyebrow">CLOUD SUSTAINABILITY / ANALYTICS</div><h1>Cloud Carbon Optimizer</h1><p>Calculate workload energy and carbon. Compare cloud regions.</p></div><button className="icon-button" onClick={loadRegions} title="Refresh regions"><RefreshCw size={18}/></button></header>
      {error && <div className="alert error"><strong>Something needs attention</strong><span>{error}</span><button onClick={() => setError('')}>Dismiss</button></div>}
      {notice && <div className="alert success"><CheckCircle2 size={18}/><span>{notice}</span></div>}
      <section className="hero-card">
        <div className="hero-copy"><div className="pill"><span className="pulse"></span> WORKLOAD INTELLIGENCE</div><h2>Make every cloud<br/><em>workload count.</em></h2><p>Calculate workload energy and carbon emissions, then compare cloud regions.</p><div className="hero-foot"><span><CheckCircle2 size={15}/> Region comparison</span><span><CheckCircle2 size={15}/> Calculation breakdown</span></div></div>
        <div className="hero-art"><div className="orbit orbit-one"></div><div className="orbit orbit-two"></div><div className="planet"><Cloud size={48}/></div><div className="float-card float-top"><Leaf size={16}/><span>Carbon-aware<br/><b>optimization</b></span></div><div className="float-card float-bottom"><Activity size={16}/><span>Regional<br/><b>comparison</b></span></div><div className="mini-dot dot-a"></div><div className="mini-dot dot-b"></div></div>
      </section>
      <div className="section-heading"><div><span className="eyebrow">01 / CONFIGURE</span><h2>Workload calculator</h2><p>Enter workload details to calculate energy use and carbon emissions.</p></div><div className="data-badge"><span></span>{regionData.regions?.length || 0} regions loaded</div></div>
      <section className="workspace-grid" id="workload">
        <div className="panel form-panel">
          <div className="panel-title"><div className="panel-icon"><Server size={18}/></div><div><h3>Workload configuration</h3><p>All fields are required unless stated otherwise.</p></div></div>
          <div className="form-grid">
            <label className="field full"><span><MapPin size={14}/> Target country / location for comparison</span><input type="text" list="available-locations" placeholder="e.g. India, Japan, Germany" value={form.location} onChange={e=>update('location',e.target.value)} /><datalist id="available-locations">{[...new Set((regionData.regions || []).map(r=>String(r.Country || '').trim()).filter(Boolean))].sort().map(country=><option key={country} value={country}/>)}</datalist><small>Used by “Compare providers & regions”. Only matching dataset locations are ranked.</small></label>
            <label className="field full"><span>Cloud provider</span><select value={form.provider} onChange={e => { const p=e.target.value; const r=(regionData.regions||[]).find(x=>String(x.Provider).toLowerCase()===p.toLowerCase()); setForm(f=>({...f,provider:p,region_code:r?.Region_Code||''})); }}><option value="">Select provider</option>{providers.map(p=><option key={p}>{p}</option>)}</select></label>
            <label className="field full"><span>Cloud region</span><select value={form.region_code} onChange={e=>update('region_code',e.target.value)}><option value="">Select region</option>{availableRegions.map((r,i)=><option key={`${r.Region_Code}-${i}`} value={r.Region_Code}>{r.Region_Name || r.Region || r.Region_Code} ({r.Region_Code})</option>)}</select></label>
            <label className="field"><span><Cpu size={14}/> CPU utilization (%)</span><input type="number" min="0" max="100" value={form.cpu_utilization} onChange={e=>update('cpu_utilization',e.target.value)}/><small>0–100%</small></label>
            <label className="field"><span><MemoryStick size={14}/> RAM (GB)</span><input type="number" min="0.1" step="0.1" value={form.ram_gb} onChange={e=>update('ram_gb',e.target.value)}/></label>
            <label className="field"><span><Database size={14}/> Storage (GB)</span><input type="number" min="0" step="1" value={form.storage_gb} onChange={e=>update('storage_gb',e.target.value)}/></label>
            <label className="field"><span><Activity size={14}/> Runtime (hours)</span><input type="number" min="0.1" step="0.1" value={form.runtime_hours} onChange={e=>update('runtime_hours',e.target.value)}/></label>
            <label className="field full"><span><Server size={14}/> Number of virtual machines</span><input type="number" min="1" step="1" value={form.vm_count} onChange={e=>update('vm_count',e.target.value)}/></label>
          </div>
          <div className="form-actions"><button className="button-secondary" onClick={()=>{setForm(initialForm);setResult(null);setOptimization(null);setError('')}}>Reset</button><button className="button-primary" disabled={busy || !form.provider || !form.region_code} onClick={calculate}>{busy?<LoaderCircle className="spin" size={17}/>:<Zap size={17}/>} Calculate footprint</button></div>
          <button className="button-optimize" disabled={busy || !form.location.trim()} onClick={optimize}>{busy?<LoaderCircle className="spin" size={17}/>:<Leaf size={17}/>} Compare providers & regions <ArrowDownRight size={16}/></button>
          {!regionData.regions?.length && <div className="empty-dataset"><Database size={18}/><div><b>Your regional dataset is not populated yet</b><p>Add real, sourced rows to the workbook sheets documented in the README. The calculator will then load provider and region choices here.</p></div></div>}
        </div>
        <div className="results-column">
          <div className="result-intro"><span className="eyebrow">02 / RESULTS</span><h3>{optimization ? 'Optimization results' : 'Your footprint snapshot'}</h3><p>{result ? `${result.region_name || result.region_code} · ${result.provider}` : 'Your results will appear here.'}</p></div>
          <div className="metric-grid">
            <Metric icon={<Zap size={17}/>} label="Energy use" value={result ? fmt(result.energy?.total_energy_kwh) : '—'} unit="kWh" tint="mint"/>
            <Metric icon={<Leaf size={17}/>} label="Carbon emissions" value={result ? fmt(result.carbon?.carbon_kg, 4) : '—'} unit="kg CO₂e" tint="green"/>
            <Metric icon={<MapPin size={17}/>} label="Carbon intensity" value={result ? fmt(result.carbon_intensity_gco2e_per_kwh, 1) : '—'} unit="gCO₂e/kWh" tint="blue"/>
            <Metric icon={<ShieldCheck size={17}/>} label="Sustainability score" value={result?.sustainability_score != null ? fmt(result.sustainability_score, 1) : 'N/A'} unit={result?.sustainability_score != null ? '/ 100' : 'not in dataset'} tint="gold"/>
          </div>
          <div className="panel recommendation-panel"><div className="recommendation-head"><div className="panel-icon green-icon"><Leaf size={18}/></div><span className="recommendation-tag">{optimization?'OPTIMIZER':'REGION ANALYSIS'}</span></div><h3>{optimization ? (optimization.recommended_region.region_name || optimization.recommended_region.region_code) : (result ? (result.region_name || result.region_code) : 'Ready when you are')}</h3><p>{optimization ? 'Highest-ranked region based on the Recommendation Index.' : (result ? 'Results for the selected region.' : 'Configure your workload, then calculate or compare regions.')}</p>{optimization && <div className="recommendation-stat"><span>Carbon emissions</span><strong>{fmt(optimization.recommended_region.carbon?.carbon_kg,4)} kg CO₂e</strong></div>}</div>
          <div className="panel mini-panel"><div className="panel-title compact"><div className="panel-icon"><BarChart3 size={17}/></div><div><h3>Calculation breakdown</h3><p>Energy by workload component</p></div></div><div className="energy-breakdown">{['cpu_energy_kwh','ram_energy_kwh','storage_energy_kwh'].map((key,i)=>{const labels=['CPU','Memory','Storage'];const value=result?.energy?.[key]||0;const total=result?.energy?.total_energy_kwh||0;return <div className="breakdown-row" key={key}><div className="breakdown-label"><span>{labels[i]}</span><b>{fmt(value,4)} kWh</b></div><div className="bar-track"><div className={`bar-fill fill-${i}`} style={{width:`${total?Math.min(100,value/total*100):0}%`}}/></div></div>})}</div></div>
        </div>
      </section>
      <section className="section-heading lower-heading"><div><span className="eyebrow">03 / COMPARE</span><h2>Regional comparison</h2><p>Compare the same workload across eligible AWS, Azure, and Google Cloud regions.</p></div></section>
      <section className="comparison-grid" id="comparison">
        <div className="panel chart-panel"><div className="panel-title"><div className="panel-icon"><BarChart3 size={18}/></div><div><h3>Emissions by region</h3><p>kg CO₂e · lower is better</p></div></div>{chartData.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height={260}><BarChart data={chartData} margin={{top:10,right:10,left:0,bottom:35}}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8eeeb"/><XAxis dataKey="name" angle={-25} textAnchor="end" interval={0} height={65} tick={{fontSize:11,fill:'#6c7b76'}}/><YAxis tick={{fontSize:11,fill:'#6c7b76'}}/><Tooltip formatter={v=>[`${fmt(v,4)} kg CO₂e`,'Emissions']}/><Bar dataKey="emissions" radius={[6,6,0,0]}>{chartData.map((x,i)=><Cell key={i} fill={i===0?'#23866b':'#a8cfc0'}/>)}</Bar></BarChart></ResponsiveContainer></div> : <EmptyChart text="Run region comparison to display results."/>}</div>
        <div className="panel table-panel"><div className="panel-title"><div className="panel-icon"><MapPin size={18}/></div><div><h3>Region ranking</h3><p>{comparisons.length} eligible regions for {optimization?.matched_location || form.location || "the selected location"}</p></div></div>{comparisons.length ? <div className="table-scroll"><table><thead><tr><th>Region</th><th>Intensity</th><th>Emissions</th><th>Sustainability</th><th>Recommendation index</th></tr></thead><tbody>{comparisons.map((r,i)=><tr key={`${r.provider}-${r.region_code}`} className={i===0?'winner-row':''}><td><div className="region-cell"><span className={i===0?'rank rank-first':'rank'}>{i+1}</span><div><b>{r.region_name || r.region_code}</b><small>{r.provider} · {r.region_code}</small></div></div>{i===0&&<span className="best-pill">BEST</span>}</td><td>{fmt(r.carbon_intensity_gco2e_per_kwh,1)}<small> g/kWh</small></td><td><b>{fmt(r.carbon?.carbon_kg,4)}</b><small> kg</small></td><td><b>{r.sustainability_score != null ? fmt(r.sustainability_score,1) : 'N/A'}</b><small> / 100</small></td><td><b>{r.recommendation_index != null ? fmt(r.recommendation_index,4) : 'N/A'}</b><small>{r.recommendation_index != null ? ' score/kg CO₂e' : ' undefined'}</small></td></tr>)}</tbody></table></div> : <EmptyChart text="Your ranking will appear after you optimize the workload."/>}</div>
      </section>
      <footer><div className="footer-brand"><Leaf size={16}/> CarbonCloud Optimizer</div><span>Cloud workload calculator and region comparison</span><span>Local development build</span></footer>
    </main>
  </div>
}

function Metric({icon,label,value,unit,tint}) { return <div className="metric-card"><div className={`metric-icon ${tint}`}>{icon}</div><span className="metric-label">{label}</span><strong>{value}</strong><small>{unit}</small></div> }
function EmptyChart({text}) { return <div className="empty-chart"><div className="empty-chart-icon"><BarChart3 size={22}/></div><p>{text}</p></div> }
