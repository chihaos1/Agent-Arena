import { useState } from "react"
import toast from 'react-hot-toast'

interface IssueCreatorProps{
    onIssueSaved: (title: string, body: string) => void
}

export default function IssueCreator({ onIssueSaved }: IssueCreatorProps) {
    const [title, setTitle] = useState('')
    const [body, setBody] = useState('')

    const handleSave = async() => {
        
        if (!title.trim() || !body.trim()) {
            toast.error('Issue title and description must be populated')
            return
        }
        
        onIssueSaved(title, body)

    }

    return (
        <div className="h-full flex flex-col bg-neon-purple rounded-lg border-2 border-neon-teal/30 p-4 font-space-mono overflow-hidden">
            <div className="mb-4">
                <h2 className="text-xl font-bold text-white tracking-widest uppercase">Create Issue</h2>
                <p className="text-muted text-sm mt-1 text-center">Create a new Github issue to ThinkNode-Test</p>
            </div>
            <div className="flex flex-col flex-1 gap-4">
                <input
                    value={title}
                    onChange={e => {
                        setTitle(e.target.value)
                        onIssueSaved(e.target.value, body)
                    }}
                    placeholder="Issue title"
                    className="bg-white/10 border border-white/100 rounded px-3 py-2 text-white/80 text-sm focus:outline-none placeholder-muted w-full text-left backdrop-blur-sm"
                />
                <textarea
                    value={body}
                    onChange={e => {
                        setBody(e.target.value)
                        onIssueSaved(title, e.target.value)
                    }}
                    placeholder="Issue description"
                    className="bg-white/10 border border-white/100 rounded px-3 py-2 text-white text-sm focus:outline-none placeholder-muted flex-1 resize-none w-full text-left backdrop-blur-sm"
                />
            </div>
        </div>
    )
}