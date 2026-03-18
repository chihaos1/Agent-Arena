import { useState } from 'react'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import AgentCard, { type AgentConfig } from './components/configure/AgentCard'
import IssueCreator from './components/configure/IssueCreator'
import RepoPreview from './components/configure/RepoView'
import './App.css'

interface Issue {
	title: string
	body: string
}

const defaultAgents = [
	{ model: 'gpt-4o', strategy_name: 'GPT-4o Deterministic', temperature: 0.0, version_id: 'strategy_a' },
	{ model: 'claude-sonnet-4-20250514', strategy_name: 'Claude Deterministic', temperature: 0.0, version_id: 'strategy_b' },
	{ model: 'gemini/gemini-2.5-flash', strategy_name: 'Gemini Flash Budget', temperature: 0.0, version_id: 'strategy_c' },
]

function App() {

	const [issue, setIssue] = useState<Issue>({ title: "", body: "" })
	const [agents, setAgents] = useState<AgentConfig[]>(defaultAgents)
	const [launched, setLaunched] = useState<boolean>(false)
	
	const handleLaunch = async() => {
		// try {
			
		// 	// Create GitHub issue
		// 	const issueRes = await fetch('https://api.github.com/repos/chihaos1/ThinkNode-Test/issues', {
		// 		method: "POST",
		// 		headers: {
		// 			Authorization: `Bearer ${import.meta.env.VITE_GITHUB_TOKEN}`,
		// 			'Content-Type': 'application/json'
		// 		},
		// 		body: JSON.stringify({ title: issue.title, body: issue.body })
		// 	})

		// 	if (!issueRes.ok) throw new Error("Failed to create GitHub issue")
			
		// 	toast.success('GitHub issue submitted')
		// 	const issueData = await issueRes.json()

		// 	// Send to FastAPI
		// 	const runRes = await fetch('http://127.0.0.1:8000')
		
		// } catch(err) {

		// }
		setLaunched(true)
		
	}

	return (
		<div className="h-screen w-full max-w-[1380px] mx-auto flex flex-col overflow-hidden p-4">
			<div>
				<h1 className="font-space-mono font-bold text-neon-teal text-3xl tracking-widest uppercase">
				Agent Arena
				</h1>
			</div>
			<div className="max-h-[75vh] flex gap-4 flex-1 overflow-hidden mt-[5vh]">
				<AnimatePresence>
					{!launched && (
						<motion.div 
							key="repo-panel"
							className="w-[35%] min-w-0 gap-4 flex items-stretch"
							exit={{ x: '-120%', opacity: 0 }}
							transition={{ duration: 0.3, ease: "easeInOut"}}
						>
							<div className="flex-1 min-w-0">
								<RepoPreview />
							</div>
							<div className="w-[2px] bg-neon-teal/20 self-stretch" />
						</motion.div>
					)}
				</AnimatePresence>
				
				



				<div className="w-[65%] flex flex-col gap-4 overflow-hidde">
					<div className="flex-[2] overflow-hidden">
						<IssueCreator 
							onIssueSaved={(title, body) => setIssue({ title, body })}
						/>
					</div>
					<div className="flex gap-3 flex-[2]">
						{ agents.map((config, i) => (
								<AgentCard 
									key={config.version_id}
									agentNumber={i + 1}
									config={config}
									onChange={
										updated => {
											const newConfigs = [...agents]
											newConfigs[i] = updated
											setAgents(newConfigs)}}
								/>))}
					</div>
				</div>
			</div>
			<div className="flex justify-end mt-[3vh]">
				<button
					onClick={handleLaunch}
					className="font-space-mono font-bold text-sm tracking-widest uppercase px-12 py-3 rounded border border-neon-teal text-neon-teal hover:bg-neon-teal hover:text-black hover:scale-105 transition-all duration-200 cursor-pointer"
				>
					Launch Run →
				</button>
			</div>
		</div>
	)
}

export default App
