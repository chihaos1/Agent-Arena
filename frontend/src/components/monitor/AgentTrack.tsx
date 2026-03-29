import { useEffect, useState } from "react"
import ArtifactModal from "./ArtifactModal"

type Step = {
    id: string
    label: string
}

const STEPS: Step[] = [
    { id: 'retrieving_context', label: 'Retrieving Context' },
    { id: 'planning', label: 'Planning' },
    { id: 'coding', label: 'Coding' },
    { id: 'creating_pr', label: 'Creating PR' },
    { id: 'result', label: 'Result' }
]

const STEP_STYLES = {
    completed: 'border-green-500 text-green-400 text-sm',
    failed: 'border-red-500 text-red-400 text-sm',
    active: 'border-neon-teal text-white text-sm',
    inactive: 'border-border text-muted text-xs',
} as const

interface AgentTrackProps {
    agentNumber: number
    currentStep: string
    artifacts: Record<string, string>
}

export default function AgentTrack({ agentNumber, currentStep, artifacts }: AgentTrackProps) {
    const [dotCount, setDotCount] = useState(1)
    const [selectedArtifact, setSelectedArtifact] = useState<{ step: string, content: string } | null>(null)

    const isFinished = currentStep === 'completed' || currentStep === 'failed'
    
    // Animate loading dots
    useEffect(() => {
        setDotCount(1)
        const interval = setInterval(() => {
            setDotCount(prev => prev === 3 ? 1 : prev + 1)
        }, 500)
        return () => clearInterval(interval)
    }, [currentStep])

    // Animate line progression
    const effectiveStep = isFinished ? 'result' : currentStep // Remap completed or failed to result when finished
    const currentStepIndex = STEPS.findIndex(s => s.id === effectiveStep)
    const litPercent = currentStepIndex >= 0 ? ((currentStepIndex + 0.5) / STEPS.length) * 100 : 0
    
    // Calculate green and red portion of the line based on success or failure
    const failedAtStep = currentStep === 'failed' && artifacts['failed'] ? (artifacts['failed'] as any)?.step : null
    const failedAtIndex = failedAtStep ? STEPS.findIndex(s => s.id === failedAtStep) : null
    const greenPercent = failedAtIndex !== null ? ((failedAtIndex + 0.5) / STEPS.length) * 100 : litPercent
    const redPercent = failedAtIndex !== null ? litPercent : 0
    
    return (
        <div className="relative flex flex-col gap-10 font-space-mono">
            
            {/* Progress Bar */}
            <div 
                className="absolute left-1/2 top-10 bottom-10 -translate-x-1/2 w-1 bg-neon-teal/20 z-0"
                aria-hidden="true"
            />

            <div
                className="absolute left-1/2 top-8 -translate-x-1/2 w-1 z-0 transition-all duration-700"
                style={{ height: `${greenPercent}%`, backgroundColor: '#1D9E75' }}
            />

            {currentStep === 'failed' && (
                <div
                    className="absolute left-1/2 -translate-x-1/2 w-1 z-0 transition-all duration-700"
                    style={{
                        top: `calc(2.3rem + ${greenPercent}%)`,
                        height: `${redPercent - greenPercent}%`,
                        backgroundColor: '#ef4444'
                    }}
                />
            )}
            
            {STEPS.map(step => {
                
                // Updates based on status
                const isActive = step.id === currentStep || (step.id === 'result' && isFinished)
                const isCompleted = step.id === 'result' && currentStep === 'completed'
                const isFailed = step.id === 'result' && currentStep === 'failed'
                const isFailedStep = currentStep === 'failed' && step.id === failedAtStep
                const artifactKey = (step.id === 'result' && isFinished) 
                    ? (currentStep === 'failed' ? 'failed' : 'completed')
                    : step.id
                
                // Determine step style based
                const styleKey = isCompleted ? 'completed' : isFailed || isFailedStep ? 'failed' : isActive ? 'active' : 'inactive'

                return (
                    <div key={step.id} className="relative z-10">
                        <div className={`rounded-lg border px-12 py-8 transition-all duration-300 bg-step-bg ${STEP_STYLES[styleKey]}`}>
                            <div className="flex flex-col items-center justify-center gap-2 h-[40px]">
                                <span className="inline-block min-w-[180px]">
                                    {
                                        step.id === 'result' && currentStep === 'completed' ? 'Completed' 
                                        : step.id === 'result' && currentStep === 'failed' ? 'Failed'
                                        : isActive && !isFinished ? `${step.label}${'.'.repeat(dotCount)}`
                                        : step.label
                                    }
                                </span>
                                {artifacts[artifactKey] && (
                                    <button
                                        onClick={() => setSelectedArtifact({ step: artifactKey, content: artifacts[artifactKey]})}
                                        className={`w-fit justify-center text-xs  border ${!isFailed ? "border-neon-teal/50 text-neon-teal hover:bg-neon-teal" : "border-red-500/50 text-red hover:bg-red-500/50"} rounded px-2 py-0.5  hover:text-black transition-all duration-200 cursor-pointer`}
                                    >
                                        {!isFailed ? "Artifact" : "Error"}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                )
            })}

            {selectedArtifact && (
                <ArtifactModal 
                    agentNumber={agentNumber}
                    step={selectedArtifact.step}
                    content={selectedArtifact.content}
                    onClose={() => setSelectedArtifact(null)}
                />
            )}
        </div>
    )
}