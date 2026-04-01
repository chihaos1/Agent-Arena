import { useEffect, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LabelList  } from "recharts"

const MODEL_COLORS: Record<string, string> = {
    "gpt-4o": "#00ffa3",
    "gemini/gemini-2.5-flash": "#f43f5e",
    "claude-sonnet-4-20250514": "#f59e0b"
}

const MODEL_LABELS: Record<string, string> = {
    "gpt-4o": "GPT-4o",
    "gemini/gemini-2.5-flash": "Gemini Flash",
    "claude-sonnet-4-20250514": "Claude Sonnet"
}

const PHASE_ORDER = ["retrieving_context", "planning", "coding", "creating_pr"]

export default function CostChart() {
    const [chartData, setChartData] = useState<Record<string, any>[]>([])

    useEffect(() => {
        const fetchCosts = async () => {
            const response = await fetch(
                `https://app.posthog.com/api/projects/340866/events/?event=%24ai_generation&limit=1000`,
                {
                    headers: {
                        'Authorization': `Bearer ${import.meta.env.VITE_POSTHOG_API_KEY}`,
                    }
                }
            )   
            const data = await response.json()
            const costs: Record<string, Record<string, number>> = {}
            
            // Aggregates total costs by phase and by models (e.g. {"gpt-4o": { "planning": 0.006 }})
            for (const event of data.results) {
                const model = event.properties.$ai_model
                const phase = event.properties.phase
                const cost = event.properties.$ai_total_cost_usd ?? 0

                if (!model || !phase || cost === 0) continue
                if (!costs[model]) costs[model] = {}
                costs[model][phase] = (costs[model][phase] ?? 0) + cost
            }
            
            const models = Object.keys(costs)

            // Check cost for phase exists
            const phases = PHASE_ORDER.filter(phase =>
                models.some(model => costs[model][phase] !== undefined)
            )
            
            // Transform data to structure that Rechart can process (e.g. { phase: "planning", "gpt-4o": 0.304, "gemini/...": 0.148, "claude-...": 0.614 })
            const transformed = phases.map(phase => {
                const entry: Record<string, any> = { phase }
                for (const model of models) {
                    entry[model] = parseFloat((costs[model][phase] ?? 0).toFixed(4))
                }
                return entry
            })

            setChartData(transformed)
        }

        fetchCosts()
    }, [])

    const models = chartData.length > 0
        ? Object.keys(chartData[0]).filter(k => k !== 'phase')
        : []

    return (
        <div className="flex flex-col w-full font-space-mono">
            <div className="flex items-center gap-3 p-3">
                <h2 className="text-neon-teal text-sm tracking-widest uppercase font-bold">Cost Breakdown</h2>
                <p className="text-muted text-xs">Total LLM cost per phase, by model.</p>
            </div>

            <div className="h-[280px] min-h-[280px] border-2 border-neon-teal/50 bg-neon-purple rounded-lg"
            >
                <ResponsiveContainer width="100%" height="100%" >
                    <BarChart 
                        data={chartData} 
                        margin={{ top: 20, right: 20, left: 10, bottom: 5 }}
                        style={{
                            background: '#111111',
                            backgroundImage: 'radial-gradient(circle, #00ffa3 1px, transparent 1px)',
                            backgroundSize: '24px 24px'
                        }}
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis
                            dataKey="phase"
                            tick={{ fill: '#ffffff', fontSize: 12, fontFamily: 'Space Mono' }}
                            tickFormatter={(val) => val.replace("_", " ")}
                        />
                        <YAxis
                            tick={{ fill: '#ffffff', fontSize: 12, fontFamily: 'Space Mono', fontWeight: 'bold' }}
                            tickFormatter={(val) => `$${val}`}
                        />
                        <Tooltip
                            cursor={{ fill: 'rgba(153, 69, 255, 0.4)' }}
                            contentStyle={{ background: '#1a1828', border: '1px solid #333', fontFamily: 'Space Mono', fontSize: 11, textAlign: "left" }}
                            formatter={(val, name) => {
                                const nameStr = String(name ?? "")
                                const num = typeof val === "number" ? val : 0
                                return [`$${num}`, MODEL_LABELS[nameStr] ?? name]
                            }}
                            labelFormatter={(label) => label.replace("_", " ").toUpperCase()}
                        />
                        <Legend
                            layout="vertical"
                            align="left"
                            verticalAlign="middle"
                            formatter={(val) => MODEL_LABELS[val] ?? val}
                            wrapperStyle={{ 
                                fontSize: 11, 
                                fontFamily: 'Space Mono',
                                background: '#9945ff',
                                padding: '8px 12px',
                                borderRadius: '4px',
                            }}
                        />
                        {models.map(model => (
                            <Bar key={model} dataKey={model} fill={MODEL_COLORS[model] ?? "#888"} radius={[2, 2, 0, 0]} activeBar={false}>
                                <LabelList 
                                    dataKey={model} 
                                    position="top" 
                                    formatter={(val) => {
                                        const num = typeof val === "number" ? val : 0
                                        return `$${num}`
                                    }}
                                    style={{ fontSize: 9, fontFamily: 'Space Mono', fill: '#ffffff' }}
                                />
                            </Bar>
                        ))}
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    )

}