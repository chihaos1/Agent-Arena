import { useEffect, useState, useMemo } from "react"
import { ReactFlow, Background } from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { buildFlowData } from './utils/funnelTransform'
import { type FunnelData } from './models/funnel'
import { FunnelNode } from './utils/FunnelNode'

const MODEL_LABELS: Record<string, string> = {
    'gpt-4o': 'GPT-4o',
    'gemini/gemini-2.5-flash': 'Gemini Flash',
    'claude-sonnet-4-20250514': 'Claude Sonnet',
}

const nodeTypes = { funnel: FunnelNode }

export default function PhaseFunnel() { 
    const [data, setData] = useState<FunnelData | null>(null)
    const [selectedModel, setSelectedModel] = useState<string | null>(null)

    // Fetch Funnel data from PostHog
    useEffect(() => {
        const fetchFunnel = async() => {
            const response = await fetch(`${import.meta.env.VITE_API_URL}/insights/funnel`)
            const data = await response.json()
            setData(data)
            setSelectedModel(data.result[0][0].breakdown_value[0])
        }

        fetchFunnel()
    }, [])

    // Find the funnel steps for the currently selected model and recalculate the nodes and edges
    const selectedSteps = (data?.result.find(model => model[0].breakdown_value[0] === selectedModel) ?? data?.result[0])
    const { nodes, edges } = useMemo(() => {
        if (!selectedSteps) return { nodes: [], edges: [] }
        return buildFlowData(selectedSteps)
    }, [selectedSteps])

    if (!data) return <p className="text-muted text-xs font-space-mono">Failed to get Funnel data...</p>

    const models = data.result.map(model => model[0].breakdown_value[0])
     
    return (
        <div className="flex flex-col w-full font-space-mono">
            <div className="flex items-center gap-3 p-3">
                <h2 className="text-neon-teal text-sm tracking-widest uppercase font-bold">Phase Funnel</h2>
                <p className="text-muted text-xs">Success rate across each agent phase, by model.</p>
            </div>
            <div className="flex w-full bg-neon-purple border-3 border-neon-teal/50 rounded-lg">

                {/* Tabs */}
                <div className="flex flex-col px-3 py-4">
                    <label className="text-left font-bold">
                        Models
                    </label>
                    {models.map(model => (
                    <button
                        key={model}
                        onClick={() => setSelectedModel(model)}
                        className={`text-left text-xs tracking-widest uppercase px-3 py-2 hover:text-neon-teal transition-all cursor-pointer ${
                                selectedModel === model
                                    ? 'text-neon-teal font-bold'
                                    : 'text-muted hover:border-neon-teal/50'
                            }`}
                    >
                        {MODEL_LABELS[model] ?? model}
                    </button>
                ))}
                </div>
                
                {/* Sankey Diagram */}
                <div className="flex-1 h-[280px]">
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        nodeTypes={nodeTypes}
                        fitView
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable={false}
                        panOnDrag={false}
                        style={{ background: '#111111' }}
                        proOptions={{ hideAttribution: true }}
                        zoomOnScroll={ false }
                    >
                        <Background color="#00ffa3" gap={16} size={1} />
                    </ReactFlow>
                </div>
            </div>
        </div>
    )
}