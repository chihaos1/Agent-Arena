import { useState, useRef } from 'react'

const SAMPLE_QUERIES = [
    "Add a character limit of 100 characters to the issue title input field with a visible counter",
    "Add a tooltip to each priority label explaining what the priority level means",
    "Add a confirmation dialog when a user tries to delete an issue"
]

export default function Guide() {
    const [visible, setVisible] = useState(() => localStorage.getItem("guide_dismissed") != "true")
    const [pos, setPos] = useState({ x: 40, y: 40 })
    const [copied, setCopied] = useState<number | null>(null)
    const dragging = useRef(false)
    const offset = useRef({ x: 0, y: 0 })

    if (!visible) return null

    const onMouseDown = (e: React.MouseEvent ) => {
        dragging.current = true
        offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }

        const onMouseMove = (e: MouseEvent) => {
            if (!dragging.current) return
            setPos({ x: e.clientX - offset.current.x, y: e.clientY - offset.current.y })
        }

        const onMouseUp = () => {
            dragging.current = false
            window.removeEventListener("mousemove", onMouseMove)
            window.removeEventListener("mouseup", onMouseUp)
        }

        window.addEventListener('mousemove', onMouseMove)
        window.addEventListener('mouseup', onMouseUp)
    }

    const dismiss = () => {
        localStorage.setItem("guide_dismissed", "true")
        setVisible(false)
    }

    const handleCopy = (query: string, i: number) => {
        navigator.clipboard.writeText(query)
        setCopied(i)
        setTimeout(() => setCopied(null), 1500)
    }

    return (
        <div
            className="fixed z-50 w-80 bg-[#1a1828] border border-neon-teal/50 rounded-lg font-space-mono shadow-lg text-left"
            style={{ left: pos.x, top: pos.y }}
        >
            {/* Header — drag handle */}
            <div
                className="flex items-center justify-between px-4 py-3 border-b border-neon-teal/20 cursor-grab active:cursor-grabbing"
                onMouseDown={onMouseDown}
            >
                <span className="text-neon-teal text-xs tracking-widest uppercase font-bold">Agent Arena - Guide</span>
                <button onClick={dismiss} className="text-muted text-xs hover:text-red-500 transition-colors cursor-pointer">✕</button>
            </div>

            {/* Content */}
            <div className="px-4 py-3 flex flex-col gap-3 text-xs text-muted leading-relaxed">
                <p className="text-left text-white">
                    Race GPT-4o, Claude Sonnet, and Gemini Flash on the same GitHub issue — compare cost, speed, and quality in real time.
                </p>

                <div className="border-t border-neon-teal/10 pt-2">
                    <p className="text-neon-teal/70 mb-2">SANDBOX REPO</p>
                    <p>Currently running on <a href="https://github.com/chihaos1/jira_clone" target="_blank" rel="noopener noreferrer" className="text-neon-teal hover:underline">chihaos1/jira_clone</a>. Custom repo support coming soon.</p>
                </div>

                <div className="border-t border-neon-teal/10 pt-2 flex flex-col gap-1">
                    <p className="text-neon-teal/70 mb-2">HOW TO USE</p>
                    <p>1. Write an issue title and description</p>
                    <p>2. Configure agents (model, temperature)</p>
                    <p>3. Press <span className="text-neon-teal">Launch Run →</span></p>
                    <p>4. Watch live progress and artifacts per step</p>
                    <p>5. Click <span className="text-neon-teal">Arena Insights</span> for cost and token analytics</p>
                </div>

                <div className="border-t border-neon-teal/10 pt-2 flex flex-col gap-2">
                    <p className="text-neon-teal/70 mb-1">SAMPLE QUERIES</p>
                    {SAMPLE_QUERIES.map((query, i) => (
                        <div key={i} className="flex flex-col gap-1 bg-[#111020] rounded p-2 border border-neon-teal/10">
                            <p className="text-white leading-relaxed">{query}</p>
                            <button
                                onClick={() => handleCopy(query, i)}
                                className="self-start text-[10px] tracking-widest uppercase px-2 py-0.5 rounded border border-neon-teal/50 text-neon-teal hover:bg-neon-teal hover:text-black transition-all duration-200 cursor-pointer"
                            >
                                {copied === i ? 'Copied!' : 'Copy this →'}
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-neon-teal/20">
                <button
                    onClick={dismiss}
                    className="w-full text-xs tracking-widest uppercase py-2 rounded border border-neon-teal/50 text-neon-teal hover:bg-neon-teal hover:text-black transition-all duration-200 cursor-pointer"
                >
                    Got it →
                </button>
            </div>
        </div>
    )
}