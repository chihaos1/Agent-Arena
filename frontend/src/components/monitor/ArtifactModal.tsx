import { useRef, useState } from 'react'

interface ArtifactModalProps {
    agentNumber: number
    step: string
  content: string | object
  onClose: () => void
}

export default function ArtifactModal({ agentNumber, step, content, onClose }: ArtifactModalProps) {
    const [pos, setPos] = useState({ x: 0, y: 0 })
    const dragging = useRef(false) // useRef will not trigger re-render mid-drag
    const startPos = useRef({ x: 0, y: 0 })

    const onMouseDown = (e: React.MouseEvent) => {
        dragging.current = true
        startPos.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
    }

    const onMouseMove = (e: React.MouseEvent) => {
        if (!dragging.current) return
        setPos({ x: e.clientX - startPos.current.x, y: e.clientY - startPos.current.y })
    }

    const onMouseUp = () => { dragging.current = false }

    const displayContent = 
        typeof content === 'string'
            ? content
            : JSON.stringify(content, null, 2)

    return (
        <div
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            style={{ position: 'fixed', top: `calc(25% + ${pos.y}px)`, left: `calc(25% + ${pos.x}px)`, zIndex: 9999 }}
            className="bg-surface border border-neon-teal/40 rounded-lg w-[60vw] max-h-[70vh] flex flex-col font-space-mono"
        >
            <div
                onMouseDown={onMouseDown}
                className="flex justify-between px-4 py-2 border-b border-neon-teal/20 cursor-move select-none"
            >
                <span className="text-neon-teal text-xs tracking-widest uppercase">
                    Agent {agentNumber} - {step}
                </span>
                <button
                    onClick={onClose}
                    className="text-muted hover:text-red-500 cursor-pointer"
                >
                    ✕
                </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 text-white/70 text-xs text-left whitespace-pre-wrap scrollbar-teal">
                {displayContent ?? 'No content available'}
            </div>
        </div>
    )
}