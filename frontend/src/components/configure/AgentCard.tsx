import { motion } from 'framer-motion'

export interface AgentConfig {
    model: string
    strategy_name: string
    temperature: number
    version_id: string
}

interface AgentCardProps {
    agentNumber: number
    launched: boolean
    config: AgentConfig
    onChange: (config: AgentConfig) => void
}

const MODELS = [
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'Claude Sonnet 4.5', value: 'claude-sonnet-4-20250514' },
  { label: 'Gemini Flash 2.5', value: 'gemini/gemini-2.5-flash' },
]

export default function AgentCard({ agentNumber, launched, config, onChange }: AgentCardProps) {

    const modelLabel = MODELS.find(m => m.value === config.model)?.label ?? config.model

    return (
        <motion.div 
            className="flex-1 flex flex-col bg-neon-purple rounded-lg border-2 border-neon-teal/30 p-4 font-space-mono">
            <h2 className="text-neon-teal font-bold tracking-widest uppercase mb-2">
                Agent {agentNumber}
            </h2>
            <hr className="mb-4"></hr>
            <div className="flex flex-col gap-4">
                <div>
                    {launched 
                        ?   <div className="flex items-center justify-between gap-2"> 
                                <label className="text-muted text-xs uppercase tracking-widest">Strategy Name:</label>
                                <p className="text-white text-xs mt-1"><strong>{config.strategy_name}</strong></p>
                            </div>
                        :   <>
                                <label className="block text-left mb-1 text-muted text-xs uppercase tracking-widest">Strategy Name</label>
                                    <input 
                                        value={config.strategy_name}
                                        onChange={e => onChange({ ...config, strategy_name: e.target.value})}
                                        placeholder="e.g. GPT-4o Deterministic"
                                        className="bg-white/10 border border-neon-teal/50 rounded px-3 py-2 text-white text-sm w-full mt-1 focus:outline-none focus:border-neon-teal placeholder-muted"
                                    />
                            </> 
                    }
                </div>
                <div>
                    {launched
                        ?   <div className="flex items-center justify-between gap-2">
                                <label className="block text-left mb-1 text-muted text-xs uppercase tracking-widest">Model:</label>
                                <p className="text-white text-xs mt-1"><strong>{modelLabel}</strong></p>
                            </div>
                        :   <>
                                <label className="block text-left mb-1 text-muted text-xs uppercase tracking-widest">Model</label>
                                <select
                                    value={config.model}
                                    onChange={e => onChange({ ...config, model: e.target.value})}
                                    className="bg-white/10 border border-neon-teal/50 rounded px-3 py-2 text-white text-sm w-full mt-1 focus:outline-none focus:border-neon-teal placeholder-muted"
                                >
                                    {MODELS.map(m => (
                                        <option 
                                            key={m.value} 
                                            value={m.value}
                                            className="bg-white text-black"
                                        >{m.label}</option>
                                    ))}
                                </select>
                            </> 
                    }
                </div>
                <div>
                    {launched 
                        ?   <div className="flex items-center justify-between gap-2">
                                <label className="block text-left mb-1 text-muted text-xs uppercase tracking-widest">Temperature:</label> 
                                    <p className="text-white text-xs mt-1"><strong>{config.temperature.toFixed(1)}</strong></p>
                            
                            </div>
                            
                        :   <>
                                <label className="block text-left mb-1 text-muted text-xs uppercase tracking-widest">
                                    Temperature: <strong>{config.temperature.toFixed(1)}</strong>
                                </label>
                                <input 
                                    type="range"
                                    min={0} max={1} step={0.1}
                                    value={config.temperature}
                                    onChange={e => onChange({ ...config, temperature: parseFloat(e.target.value) })}
                                    className="w-full mt-1 slider"
                                />
                                <div className="flex justify-between text-muted text-xs mt-1">
                                    <span>0.0 Precise</span>
                                    <span>1.0 Creative</span>
                                </div>
                            </>
                    }
                    
                    
                </div>
            </div>
        </motion.div>
    )
}