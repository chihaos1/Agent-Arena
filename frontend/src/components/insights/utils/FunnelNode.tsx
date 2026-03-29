import { Handle, Position } from "@xyflow/react"

export const FunnelNode = ({ data }: any) => (
    <div className={`px-4 py-1 rounded border-l-4 border-t border-r border-b font-space-mono ${
        data.isDrop
            ? 'bg-[#1a1828] border-red-500 text-red-400'
            : 'bg-[#1a1828] border-neon-teal text-neon-teal'
    }`}>
        <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
        <div className="flex flex-col gap-1">
            <span className="text-[9px] uppercase tracking-widest opacity-70">{data.label}</span>
            <span className="text-lg font-bold text-white">{data.count}</span>
            {!data.isDrop && data.conversion !== undefined && (
                <span className="text-[9px] text-white/60">{data.conversion}% conv</span>
            )}
        </div>
        <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
)