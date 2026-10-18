"use client";

import Link from "next/link";

export default function ProjectDescriptionPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-10 text-slate-900">
      {/* Hero Header Section */}
      <div className="border-b border-slate-200 pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
            System Architecture · Scientific Methodology · 2016–2026
          </span>
        </div>
        <h1 className="text-3xl lg:text-4xl font-black tracking-tight text-slate-900">
          Latur Drought Intelligence Platform
        </h1>
        <p className="text-sm text-slate-600 mt-2 max-w-4xl leading-relaxed">
          An operational, high-resolution remote sensing and climatological platform monitoring meteorological, agricultural, and hydrological drought across <strong>10 tehsils and 954 revenue villages</strong> in Latur District, Marathwada. Driven by multi-spectral Sentinel-2 imagery (10m), CHIRPS satellite precipitation, and transparent multi-index synthesis compliant with the <em>Manual for Drought Management (Govt. of India)</em>.
        </p>

        {/* Quick KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs">
            <div className="text-[10px] font-bold uppercase text-slate-500">Spatial Domain</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">Latur District</div>
            <div className="text-xs text-amber-700 font-medium">10 Tehsils · 954 Villages</div>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs">
            <div className="text-[10px] font-bold uppercase text-slate-500">Temporal Coverage</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">2016–2026</div>
            <div className="text-xs text-blue-700 font-medium">98 Monthly Periods</div>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs">
            <div className="text-[10px] font-bold uppercase text-slate-500">Primary Core Metric</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">CDI Composite</div>
            <div className="text-xs text-emerald-700 font-medium">6 Fused Indices (0..1)</div>
          </div>
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs">
            <div className="text-[10px] font-bold uppercase text-slate-500">Resolution & Scale</div>
            <div className="text-lg font-black text-slate-900 mt-0.5">Cadastral Level</div>
            <div className="text-xs text-purple-700 font-medium">10m Sentinel-2 MSI</div>
          </div>
        </div>
      </div>

      {/* 1. Project Background & Context */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-5 rounded-sm bg-amber-600" />
          <h2 className="text-xl font-black text-slate-900">
            1. Geographic & Hydrological Context
          </h2>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4 text-xs md:text-sm text-slate-700 leading-relaxed">
          <p>
            Latur District is situated in the rain-shadow Deccan plateau region of Marathwada, Maharashtra (Latitude 17°52′ N to 18°50′ N, Longitude 76°12′ E to 77°18′ E), spanning an area of 7,157 km². The district experiences semi-arid climatic conditions with an average annual precipitation of 750–800 mm, concentrated heavily during the South-West Indian Summer Monsoon (June to September).
          </p>
          <p>
            In recent decades, Marathwada has become one of the most drought-vulnerable agrarian belts in South Asia, characterized by recurring meteorological deficits, severe depletion of the Manjara river basin, and critical depletion of deep basaltic aquifers. The historic 2015–2016 crisis required emergency drinking water transport via Indian Railways ("Jaldoot" water train) to supply Latur city.
          </p>
          <p>
            Traditional district-level rainfall gauges fail to capture sharp micro-climatic gradients and localized rain shadows between eastern tehsils (such as Deoni and Udgir) and western tehsils (such as Ausa and Nilanga). This platform solves the spatial resolution gap by computing individual cadastral drought signatures for every single one of Latur's 954 villages.
          </p>
        </div>
      </section>

      {/* 2. Scientific Methodology & Index Formulation */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-5 rounded-sm bg-blue-600" />
          <h2 className="text-xl font-black text-slate-900">
            2. Multi-Scale Drought Indices & Synthesis
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Multi-Scale WMO SPI Suite */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-blue-800">
                WMO Standardized Precipitation Index (SPI)
              </span>
              <span className="text-[10px] font-mono bg-blue-50 text-blue-800 px-2 py-0.5 rounded font-bold">
                CHIRPS 0.05°
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Standardized departure of precipitation fitted to a two-parameter Gamma distribution over long-term historical climatology. Evaluated across 4 distinct accumulation windows:
            </p>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <strong className="text-slate-900">SPI-1 (1-Month)</strong>: Immediate meteorological precipitation anomaly.
                </div>
                <span className="text-[10px] font-mono text-cyan-800 font-bold">Met Stress</span>
              </div>
              <div className="p-2.5 rounded-xl bg-blue-50/60 border border-blue-200 flex justify-between items-center">
                <div>
                  <strong className="text-blue-900">SPI-3 (3-Month)</strong>: Agricultural root-zone soil moisture deficit during crop vegetative phases.
                </div>
                <span className="text-[10px] font-mono text-blue-800 font-bold">Agri Stress</span>
              </div>
              <div className="p-2.5 rounded-xl bg-indigo-50/60 border border-indigo-200 flex justify-between items-center">
                <div>
                  <strong className="text-indigo-900">SPI-6 (6-Month)</strong>: Cumulative monsoon seasonal performance and reservoir inflow deficit.
                </div>
                <span className="text-[10px] font-mono text-indigo-800 font-bold">Seasonal</span>
              </div>
              <div className="p-2.5 rounded-xl bg-purple-50/60 border border-purple-200 flex justify-between items-center">
                <div>
                  <strong className="text-purple-900">SPI-12 (12-Month)</strong>: Multi-season hydrological deficit and deep groundwater recharge drawdown.
                </div>
                <span className="text-[10px] font-mono text-purple-800 font-bold">Groundwater</span>
              </div>
            </div>
          </div>

          {/* Optical Satellite Vegetation Indices */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-emerald-800">
                Optical Satellite Vegetation Suite
              </span>
              <span className="text-[10px] font-mono bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded font-bold">
                Sentinel-2 MSI (10m)
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Optical surface reflectance measurements from Sentinel-2 Level-2A surface reflectance, cloud-masked and aggregated per cadastral polygon:
            </p>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <strong className="text-slate-900">NDVI</strong>: (NIR - Red) / (NIR + Red) measuring chlorophyll absorption and canopy biomass.
                </div>
                <span className="text-[10px] font-mono text-emerald-800 font-bold">Biomass</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div>
                  <strong className="text-slate-900">EVI</strong>: Atmospheric and soil-background corrected enhanced vegetation index.
                </div>
                <span className="text-[10px] font-mono text-emerald-800 font-bold">Canopy</span>
              </div>
              <div className="p-2.5 rounded-xl bg-amber-50/60 border border-amber-200 flex justify-between items-center">
                <div>
                  <strong className="text-amber-900">VCI</strong>: 10-Year historical min-max normalization: (NDVI - min) / (max - min) * 100.
                </div>
                <span className="text-[10px] font-mono text-amber-800 font-bold">Condition</span>
              </div>
              <div className="p-2.5 rounded-xl bg-amber-50/60 border border-amber-200 flex justify-between items-center">
                <div>
                  <strong className="text-amber-900">VHI</strong>: Vegetation Health Index integrating thermal condition and greenness dynamics.
                </div>
                <span className="text-[10px] font-mono text-amber-800 font-bold">Health</span>
              </div>
            </div>
          </div>
        </div>

        {/* CDI Composite Formula Banner */}
        <div className="p-5 rounded-2xl border border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase tracking-wider text-amber-900">
              Composite Multi-Index Drought Index (CDI) Formulation
            </span>
            <span className="text-xs font-mono font-bold text-amber-800">
              Version: cdi-v2026.10
            </span>
          </div>
          <p className="text-xs text-amber-950 leading-relaxed font-medium">
            To provide a transparent, explainable, and policy-actionable indicator, the platform retires opaque "black box" machine learning classifiers in favor of an authoritative, weighted multi-criteria synthesis:
          </p>
          <div className="p-3 bg-white rounded-xl border border-amber-200 font-mono text-xs font-bold text-amber-900 overflow-x-auto text-center shadow-2xs">
            CDI = (0.30 × SPI-3_norm) + (0.20 × VHI_norm) + (0.15 × VCI_norm) + (0.15 × NDVI_norm) + (0.10 × EVI_norm) + (0.10 × PCI_norm)
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-center text-xs">
            <div className="p-2 rounded-lg bg-white border border-slate-200">
              <span className="font-bold text-emerald-800">None</span>
              <div className="text-[10px] text-slate-500 font-mono">CDI &lt; 0.20</div>
              <div className="text-[9px] text-emerald-700">Normal</div>
            </div>
            <div className="p-2 rounded-lg bg-yellow-50 border border-yellow-200">
              <span className="font-bold text-yellow-800">D0</span>
              <div className="text-[10px] text-slate-500 font-mono">0.20 – 0.35</div>
              <div className="text-[9px] text-yellow-700">Abnormally Dry</div>
            </div>
            <div className="p-2 rounded-lg bg-amber-50 border border-amber-200">
              <span className="font-bold text-amber-900">D1</span>
              <div className="text-[10px] text-slate-500 font-mono">0.35 – 0.50</div>
              <div className="text-[9px] text-amber-700">Moderate</div>
            </div>
            <div className="p-2 rounded-lg bg-orange-50 border border-orange-200">
              <span className="font-bold text-orange-900">D2</span>
              <div className="text-[10px] text-slate-500 font-mono">0.50 – 0.65</div>
              <div className="text-[9px] text-orange-700">Severe</div>
            </div>
            <div className="p-2 rounded-lg bg-red-50 border border-red-200">
              <span className="font-bold text-red-900">D3</span>
              <div className="text-[10px] text-slate-500 font-mono">0.65 – 0.80</div>
              <div className="text-[9px] text-red-700">Extreme</div>
            </div>
            <div className="p-2 rounded-lg bg-rose-50 border border-rose-300">
              <span className="font-bold text-rose-950">D4</span>
              <div className="text-[10px] text-slate-500 font-mono">≥ 0.80</div>
              <div className="text-[9px] text-rose-700">Exceptional</div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Statutory Government Trigger Framework */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-5 rounded-sm bg-rose-600" />
          <h2 className="text-xl font-black text-slate-900">
            3. Statutory Framework (Manual for Drought Management)
          </h2>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4 text-xs md:text-sm text-slate-700 leading-relaxed">
          <p>
            Under the national framework prescribed by the Ministry of Agriculture & Farmers Welfare (Government of India) and the State Government of Maharashtra, formal drought declaration requires the simultaneous activation of two independent diagnostic tiers:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/50 space-y-2">
              <span className="font-black text-rose-900 uppercase">Trigger 1: Meteorological Deficit</span>
              <p className="text-rose-950">
                Triggered when cumulative rainfall deficit exceeds 20% compared to historical normal, or when the 3-month Standardized Precipitation Index satisfies <strong>SPI-3 ≤ -1.0</strong>. Severe meteorological drought occurs when rainfall deficit exceeds 60% or SPI-3 ≤ -1.5.
              </p>
            </div>
            <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/50 space-y-2">
              <span className="font-black text-amber-900 uppercase">Trigger 2: Agricultural & Vegetation Impact</span>
              <p className="text-amber-950">
                Evaluates remote sensing impact on standing crops. Triggered when NDVI departure from normal satisfies <strong>ΔNDVI ≤ -20%</strong> or when the Vegetation Condition Index drops below <strong>VCI ≤ 40%</strong>. Severe impact is recorded at ΔNDVI ≤ -30% or VCI ≤ 20%.
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-600">
            When both triggers are concurrently active, the administrative unit automatically qualifies for formal State Disaster Response Fund (SDRF) notification, agricultural input subsidy disbursement, loan restructuring, and priority mobilization of drinking water tanker convoys.
          </p>
        </div>
      </section>

      {/* 4. Full-Stack End-to-End Technology Stack */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-5 rounded-sm bg-purple-600" />
          <h2 className="text-xl font-black text-slate-900">
            4. Architecture & Engineering Pipeline
          </h2>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="text-[10px] font-bold uppercase text-amber-700">Data & Scientific Processing</div>
              <h3 className="font-black text-slate-900 text-sm">Python + GEE Engine</h3>
              <p className="text-slate-600 leading-relaxed">
                Autonomous raster ingestion via Google Earth Engine (Sentinel-2 L2A + CHIRPS monthly). Scientific processing via GDAL, Rasterio, SciPy Gamma distribution fitting, and GeoPandas zonal extraction.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="text-[10px] font-bold uppercase text-blue-700">Spatial Backend & API</div>
              <h3 className="font-black text-slate-900 text-sm">Go Microservice + Edge API</h3>
              <p className="text-slate-600 leading-relaxed">
                High-throughput Go API server using Chi and pgx connection pooling. Next.js edge router providing sub-5ms caching for village timeseries, monthly matrices, and cadastral spatial geometry.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="text-[10px] font-bold uppercase text-emerald-700">Analytical Frontend</div>
              <h3 className="font-black text-slate-900 text-sm">Next.js 14 App Router</h3>
              <p className="text-slate-600 leading-relaxed">
                Interactive Google Terrain vector choropleths rendered via React-Leaflet, bi-temporal curtain slider with GPU-accelerated clipPath, and 98-period statistical timeseries charts with Recharts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Direct Navigation Links */}
      <section className="p-6 rounded-2xl border border-slate-200 bg-white shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-black text-slate-900">Explore Latur Observatory Live</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Access the continuous 10-year observation record, cadastral maps, and bi-temporal curtain slider.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs font-bold">
          <Link
            href="/"
            className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white shadow-xs transition-colors"
          >
            Open Live Map
          </Link>
          <Link
            href="/timeseries"
            className="px-4 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition-colors"
          >
            Time Series Charts
          </Link>
          <Link
            href="/compare"
            className="px-4 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition-colors"
          >
            Comparison Slider
          </Link>
          <Link
            href="/animation"
            className="px-4 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition-colors"
          >
            10-Yr Timelapse
          </Link>
        </div>
      </section>
    </div>
  );
}
