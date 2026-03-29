import PhaseFunnel from "./PhaseFunnel"
import CostChart from "./CostChart"
import TokenChart from "./TokensChart"

interface InsightsPageProps {
    onClose: () => void
}

export default function InsightsPage({ onClose }: InsightsPageProps) {
    return (
        <div>
            <div className="flex items-center justify-center gap-3 mt-3">
                <div className="font-space-mono text-neon-teal">
                    <span className="text-m tracking-widest">Insights</span> 
                </div>
            </div>
            <div className="flex flex-col gap-6 mt-4">
                <PhaseFunnel />
                <CostChart />
                <TokenChart />
            </div>
            <button 
                className="w-64 flex items-center justify-center mt-8 font-space-mono font-bold text-sm tracking-widest uppercase py-3 rounded border border-neon-teal text-neon-teal hover:bg-neon-teal hover:text-black hover:scale-105 transition-all duration-200 cursor-pointer"
                onClick={onClose}
            >
                ← Back
            </button>
        </div>
    )
}