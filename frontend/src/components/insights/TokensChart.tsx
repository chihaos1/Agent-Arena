import { Fragment, useEffect, useState } from "react"
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

export default function TokenChart() {
    const [chartData, setChartData] = useState<Record<string, any>[]>([])

    useEffect(() => {
        const fetchTokens = async () => {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/insights/events`)
            const data = await response.json()

            // Track input and output tokens by model (e.g. { "gpt-4o": { "planning": { input: 1200, output: 340 } } })
            const tokens: Record<string, Record<string, { input: number, output: number }>> = {}
            
            // Aggregates total costs by phase and by models (e.g. {"gpt-4o": { "planning": 0.006 }})
            for (const event of data.results) {
                const model = event.properties.$ai_model
                const phase = event.properties.phase
                const input = event.properties.$ai_input_tokens ?? 0
                const output = event.properties.$ai_output_tokens ?? 0

                if (!model || !phase || (input === 0 && output === 0)) continue

                // Insert token to model
                if (!tokens[model]) tokens[model] = {}
                if (!tokens[model][phase]) tokens[model][phase] = { input: 0, output: 0 }

                tokens[model][phase].input += input
                tokens[model][phase].output += output
            }

            const models = Object.keys(tokens)

            // Check cost for phase exists
            const phases = PHASE_ORDER.filter(phase =>
                models.some(model => tokens[model][phase] !== undefined)
            )
            
            // Transform data to structure that Rechart can process (e.g. e.g. { phase: "planning", "gpt-4o_input": 89098, "gpt-4o_output": 8145, ... })
            const transformed = phases.map(phase => {
                const entry: Record<string, any> = { phase }
                for (const model of models) {
                    entry[`${model}_input`] = tokens[model][phase]?.input ?? 0
                    entry[`${model}_output`] = tokens[model][phase]?.output ?? 0
                }
                return entry
            })

            setChartData(transformed)
        }

        fetchTokens()
    }, [])

    const models = chartData.length > 0
        ? [...new Set( //Remove duplicates
            Object.keys(chartData[0])
                .filter(key => key !== "phase")
                .map(key => key.replace("_input", "").replace("_output", ""))
        )]
        : []

    return (

        <div className="flex flex-col w-full font-space-mono">
            <div className="flex items-center gap-3 p-3">
                <h2 className="text-neon-teal text-sm tracking-widest uppercase font-bold">Token Usage</h2>
                <p className="text-muted text-xs">Input vs output tokens per phase, by model.</p>
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
                            tickFormatter={(val) => val.replace(/_/g, ' ')}
                        />
                        <YAxis
                            tick={{ fill: '#ffffff', fontSize: 12, fontFamily: 'Space Mono', fontWeight: 'bold' }}
                            tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                        />
                        <Tooltip
                            cursor={{ fill: 'rgba(153, 69, 255, 0.4)' }}
                            contentStyle={{ background: '#1a1828', border: '1px solid #333', fontFamily: 'Space Mono', fontSize: 11 }}
                            formatter={(val, name) => {
                                const nameStr = String(name ?? '')
                                const isInput = nameStr.endsWith('_input')
                                const model = nameStr.replace('_input', '').replace('_output', '')
                                const num = typeof val === 'number' ? val : 0
                                return [`${num.toLocaleString()} tokens`, `${MODEL_LABELS[model] ?? model} (${isInput ? 'input' : 'output'})`]
                            }}
                            labelFormatter={(label) => label.replace(/_/g, ' ').toUpperCase()}
                        />
                        <Legend
                            layout="vertical"
                            align="left"
                            verticalAlign="middle"
                            formatter={(val) => {
                                const isInput = val.endsWith('_input')
                                const model = val.replace('_input', '').replace('_output', '')
                                return `${MODEL_LABELS[model] ?? model} (${isInput ? 'in' : 'out'})`
                            }}
                            wrapperStyle={{
                                fontSize: 10,
                                fontFamily: 'Space Mono',
                                background: '#9945ff',
                                padding: '8px 12px',
                                borderRadius: '4px',
                            }}
                        />
                        {models.map(model => (
                            <Fragment key={model}>
                                <Bar key={`${model}_input`} dataKey={`${model}_input`} stackId={model} fill={MODEL_COLORS[model] ?? "#888"} radius={[0, 0, 0, 0]} activeBar={false}>
                                    <LabelList
                                        dataKey={`${model}_input`}
                                        position="top"
                                        formatter={(val: any) => `${Math.round((val + 0) / 1000)}k`}
                                        style={{ fontSize: 9, fontFamily: 'Space Mono', fill: '#ffffff' }}
                                    />
                                </Bar>
                                <Bar key={`${model}_output`} dataKey={`${model}_output`} stackId={model} fill={`${MODEL_COLORS[model]}99`} radius={[2, 2, 0, 0]} activeBar={false} >
                                    <LabelList
                                        dataKey={`${model}_output`}
                                        position="top"
                                        formatter={(val: any) => `${Math.round((val + 0) / 1000)}k`}
                                        style={{ fontSize: 9, fontFamily: 'Space Mono', fill: '#ffffff' }}
                                    />
                                </Bar>
                            </Fragment>
                        ))}
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    )

}