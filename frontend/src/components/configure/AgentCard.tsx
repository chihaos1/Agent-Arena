import { useState } from 'react'
import { motion, AnimatePresence  } from 'framer-motion'

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
    allFinished?: boolean
    summary?: Record<string, any>
}

const MODELS = [
  { label: 'GPT-4o', value: 'gpt-4o' },
  { label: 'Claude Sonnet 4.5', value: 'claude-sonnet-4-20250514' },
  { label: 'Gemini Flash 2.5', value: 'gemini/gemini-2.5-flash' },
]

export default function AgentCard({ agentNumber, launched, config, onChange, allFinished, summary }: AgentCardProps) {

    const modelLabel = MODELS.find(m => m.value === config.model)?.label ?? config.model
    const [expanded, setExpanded] = useState<boolean>(false)

    return (
        <motion.div 
            className="relative flex-1 flex flex-col bg-neon-purple rounded-lg border-2 border-neon-teal/30 p-4 font-space-mono">
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
                                    className="bg-white/10 border border-neon-teal/50 rounded px-3 py-2 text-white text-sm w-full mt-1 focus:outline-none focus:border-neon-teal placeholder-muted cursor-pointer"
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

            {/* Expand Toggle */}
            {allFinished && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    transition={{ duration: 0.4 }}
                    className="overflow-hidden"
                >
                    <hr className="mt-4 mb-4"></hr>
                    <button
                        onClick={() => setExpanded(prev => !prev)}
                        className="text-xs text-muted tracking-widest uppercase text-neon-teal transition-colors cursor-pointer w-full text-left"
                    >
                        {expanded ? '▼ Results' : '▲ Results'}
                    </button>
                </motion.div>
            )}

            {/* Expanded Section */}
            <div className="absolute left-5 right-5 top-full overflow-hidden z-20" style={{ top: 'calc(100% + 0.5px)' }}>
                <AnimatePresence>
                    {expanded && (
                    <motion.div
                        initial={{ y: '-100%' }}
                        animate={{ y: 0 }}
                        exit={{ y: '-100%' }}
                        transition={{ duration: 0.1, ease: "easeOut" }}
                        className="bg-neon-purple/95 border-2 border-neon-teal/30 rounded-b-lg p-4"
                        style={{
                            backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.20) 1px, transparent 1px)',
                            backgroundSize: '16px 16px'
                        }}
                    >
                        <div className="flex flex-col gap-4">
                            <div className="flex items-center justify-between gap-2"> 
                                <label className="text-muted text-xs uppercase tracking-widest">Status:</label>
                                <p className="text-white text-xs mt-1"><strong className={`${summary?.failed_at_step ? 'text-red-400' : 'text-green-400'}`}>{summary?.failed_at_step ? 'Failed' : 'Completed'}</strong></p>
                            </div>
                            <div className="flex items-center justify-between gap-2"> 
                                <label className="text-muted text-xs uppercase tracking-widest">Duration:</label>
                                <p className="text-white text-xs mt-1">{summary?.duration_seconds ?? '—'}</p>
                            </div>
                            <div className="flex items-center justify-between gap-2"> 
                                <label className="text-muted text-xs uppercase tracking-widest">Cost:</label>
                                <p className="text-white text-xs mt-1">{summary?.estimated_cost_usd ?? '—'}</p>
                            </div>
                            <div className="flex items-center justify-between gap-2"> 
                                <label className="text-muted text-xs uppercase tracking-widest">Files:</label>
                                <p className="text-white text-xs mt-1">{summary?.files_generated ?? '—'}</p>
                            </div>
                            {summary?.pr_url && (
                                <>
                                    <hr />
                                    <a
                                        href={summary.pr_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-xs text-white hover:underline text-right font-bold block"
                                    >
                                        View PR →
                                    </a>
                                </>
                                
                            )}
                        </div>
                        
                    </motion.div>
                )}
                </AnimatePresence>
            </div>
        </motion.div>
    )
}