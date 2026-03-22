import { useState } from 'react'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import AgentCard, { type AgentConfig } from './components/configure/AgentCard'
import IssueCreator from './components/configure/IssueCreator'
import RepoPreview from './components/configure/RepoView'
import AgentTrack from './components/monitor/AgentTrack'
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

const animationDuration: number = 0.3

function App() {

	const [issue, setIssue] = useState<Issue>({ title: "", body: "" })
	const [agents, setAgents] = useState<AgentConfig[]>(defaultAgents)
	const [launched, setLaunched] = useState<boolean>(false)
	const [animComplete, setAnimComplete] = useState(false)

	// Update agent states
	const [agentSteps, setAgentSteps] = useState<Record<string, string>>({
		strategy_a: 'retrieving_context',
		strategy_b: 'retrieving_context',
		strategy_c: 'retrieving_context'
	})

	const [agentArtifacts, setAgentArtifacts] = useState<Record<string, Record<string, string>>>({
		strategy_a: {},
		strategy_b: {},
		strategy_c: {},
	})

	const handleLaunch = async() => {
		
		if (!issue.title.trim() || !issue.body.trim()) {
            toast.error('Issue title and description must be populated')
            return
        }
		
		setLaunched(true)
		setTimeout(() => setAnimComplete(true), animationDuration * 1000)
        
        
		
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
		try {
			const response = await fetch("http://127.0.0.1:8000/arena/stream", {
				method: "POST",
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					issue_id: '1',
					issue_description: issue.body,
					repo_name: 'chihaos1/ThinkNode-Test',
					github_token: import.meta.env.VITE_GITHUB_TOKEN,
					branch_name: 'main',
					strategies: agents
				})
			})

			const reader = response.body!.getReader()
    		const decoder = new TextDecoder()

			while (true) {
				const { done, value } = await reader.read()
				if (done) break
			
				decoder.decode(value)
					.split("\n")
					.filter(line => line.startsWith("data: "))
					.forEach(line => {
						const event = JSON.parse(line.slice(6))
						if (event.event !== "done") {
							setAgentSteps(prev => ({ ...prev, [event.version_id]: event.current_step}))
							if (event.artifact) {
								setAgentArtifacts(prev => ({
									...prev,
									[event.version_id]: {
										...prev[event.version_id],
										[event.completed_step]: event.artifact
									}
								}))
							}
						}
					})
			}

		} catch (err) {
			console.error('SSE error:', err)
			toast.error('Failed to launch run')
		}

		
	}

	return (
		<div className="h-screen w-full max-w-[1380px] mx-auto flex flex-col overflow-hidden p-4 relative">
			<div>
				<h1 className="font-space-mono font-bold text-neon-teal text-3xl tracking-widest uppercase">
					Agent Arena
				</h1>
				{animComplete && (
					<div className="flex items-center justify-center gap-3 mt-3">
						<div className="font-space-mono text-neon-teal">
							<span className="text-m tracking-widest">working on: </span> 
							<span className="font-bold text-xl ">{issue.title}</span>
						</div>
					</div>
				)}
			</div>

			{/* Pre-Launch */}
			{!launched && (
				<>
					<div className="max-h-[75vh] flex gap-4 flex-1 overflow-hidden mt-[5vh]">
						<AnimatePresence>
							<motion.div 
								key="repo-panel"
								className="w-[35%] min-w-0 gap-4 flex items-stretch"
								exit={{ x: '-120%', opacity: 0 }}
								transition={{ duration: animationDuration, ease: "easeInOut"}}
							>
								<div className="flex-1 min-w-0">
									<RepoPreview />
								</div>
								<div className="w-[2px] bg-neon-teal/20 self-stretch" />
							</motion.div>
						</AnimatePresence>
						<div className={`${animComplete  ? 'w-full' : 'w-[65%]'} flex flex-col gap-4 overflow-hidde`}>	
							<AnimatePresence>
								<motion.div
									className="flex flex-col gap-4 flex-1 overflow-hidden"
									exit={{ x: '120%', opacity: 0 }}
									transition={{ duration: animationDuration, ease: 'easeInOut' }}
								>
									<div className="flex-[2] overflow-hidden">
										<IssueCreator
											onIssueSaved={(title, body) => setIssue({ title, body })}
										/>
									</div>
									<div className="flex gap-3 flex-[1.2]">
										{agents.map((config, i) => (
											<AgentCard
												key={config.version_id}
												agentNumber={i + 1}
												launched={launched}
												config={config}
												onChange={updated => {
													const newConfigs = [...agents]
													newConfigs[i] = updated
													setAgents(newConfigs)
												}}
											/>
										))}
									</div>
								</motion.div>	
							</AnimatePresence>
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
				</>
			)}

			{/* Post-Launch */}
			{animComplete && (
				<>
					{/* Agent Cards */}
					<motion.div
						className="absolute flex gap-8 w-full h-[15vh]"
						style={{ top: 'calc(5vh + 55px)', left: 0, paddingInline: '1rem' }}
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						transition={{ duration: 0.5 }}
					>
						{agents.map((config, i) => (
							<AgentCard
								key={config.version_id}
								agentNumber={i + 1}
								launched={launched}
								config={config}
								onChange={updated => {
									const newConfigs = [...agents]
									newConfigs[i] = updated
									setAgents(newConfigs)
								}}
							/>
						))}
					</motion.div>

					{/* Agent Tracks */}
					<motion.div
						className="absolute flex gap-3 w-full"
						style={{ top: 'calc(5vh + 60px + 18vh + 1rem)', left: 0, paddingInline: '1rem' }}
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						transition={{ duration: 0.5, delay: 0.2 }}
					>
						{agents.map((config, i) => (
							<div key={config.version_id} className="flex-1 flex flex-col items-center gap-2">
								<AgentTrack 
									agentNumber={i + 1}
									currentStep={agentSteps[config.version_id]}
									artifacts={agentArtifacts[config.version_id]}
								/>
							</div>
						))}
					</motion.div>
				</>
			)}		
		</div>
	)
}

export default App
