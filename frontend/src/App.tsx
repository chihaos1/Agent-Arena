import { useState } from 'react'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import AgentCard, { type AgentConfig } from './components/configure/AgentCard'
import IssueCreator from './components/configure/IssueCreator'
import RepoPreview from './components/configure/RepoView'
import AgentTrack from './components/monitor/AgentTrack'
import InsightsPage from './components/insights/InsightsPage'
import Guide from './components/common/Guide'
import insightsImg from './assets/icons/insights.png'
import insightsHoveredImg from './assets/icons/insightsHovered.png'
import './App.css'

interface Issue {
	title: string
	body: string
}

type AgentState = {
	step: string
	artifacts: Record<string, string>
	finished: boolean
	summary: any
}

const defaultAgentState = (): AgentState => ({
	step: "retrieving_context",
	artifacts: {},
	finished: false,
	summary: null
})

const defaultAgents = [
	{ model: 'gpt-4o', strategy_name: 'GPT-4o Deterministic', temperature: 0.0, version_id: 'strategy_a' },
	{ model: 'claude-sonnet-4-20250514', strategy_name: 'Claude Deterministic', temperature: 0.0, version_id: 'strategy_b' },
	{ model: 'gemini/gemini-2.5-flash', strategy_name: 'Gemini Flash Budget', temperature: 0.0, version_id: 'strategy_c' },
]

const repoName: string = "chihaos1/jira_clone"
const animationDuration: number = 0.3

function App() {

	const [issue, setIssue] = useState<Issue>({ title: "", body: "" })
	const [agents, setAgents] = useState<AgentConfig[]>(defaultAgents)
	const [launched, setLaunched] = useState<boolean>(false)
	const [animComplete, setAnimComplete] = useState(false)
	const [insightClicked, setInsightClicked] = useState(false)
	const [insightHovered, setInsightHovered] = useState(false)

	// Update agent states
	const [agentState, setAgentState] = useState<Record<string, AgentState>>({
		strategy_a: defaultAgentState(),
		strategy_b: defaultAgentState(),
		strategy_c: defaultAgentState(),
	})

	const createGithubIssue = async(): Promise<number> => {
		const issueResponse = await fetch(`http://127.0.0.1:8000/repo/create-issue`, {
			method: "POST",
			headers: {
            	'Content-Type': 'application/json'
			},
			body: JSON.stringify({ repo_name: repoName, title: issue.title, body: issue.body })
		})

		if (!issueResponse.ok) toast.error('Failed to create Github issue')
			
		const issueData = await issueResponse.json()
		toast.success("GitHub issue submitted")

		return issueData.number
	}

	const streamArenaRun = async(issueNumber: number) => {
		const arenaResponse = await fetch("http://127.0.0.1:8000/arena/stream", {
			method: "POST",
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				issue_id: String(issueNumber),
				issue_description: issue.body,
				repo_name: repoName,
				strategies: agents
			})
		})

		const reader = arenaResponse.body!.getReader()
		const decoder = new TextDecoder()

		// Process streaming chunks
		while (true) {
			const { done, value } = await reader.read()
			if (done) break

			decoder.decode(value)
				.split("\n")
				.filter(line => line.startsWith("data: "))
				.forEach(line => {
					const event = JSON.parse(line.slice(6))
					if (event.event != "done") {
						setAgentState(prev => ({
							...prev,
							[event.version_id]: {
								...prev[event.version_id],
								step: event.current_step,
								finished: event.current_step === "completed" || event.current_step === "failed",
								summary: event.summary ?? prev[event.version_id].summary,
								artifacts: event.artifact
								? { ...prev[event.version_id].artifacts, [event.completed_step]: event.artifact}
								: prev[event.version_id].artifacts
							}
						}))
					}
				})
		}
	}

	// After launching the agents
	const handleLaunch = async() => {
		
		if (!issue.title.trim() || !issue.body.trim()) {
            toast.error('Issue title and description must be populated')
            return
        }
		
		setLaunched(true)
		setTimeout(() => setAnimComplete(true), animationDuration * 1000)

		try {
			const issueNumber = await createGithubIssue()
			await streamArenaRun(issueNumber)
		} catch(err) {
			toast.error('Failed to launch run')
		}
	}

	const allFinished = Object.values(agentState).every(a => a.finished)

	const handleReset = () => {
		setLaunched(false)
		setAnimComplete(false)
		setAgentState({
			strategy_a: defaultAgentState(),
			strategy_b: defaultAgentState(),
			strategy_c: defaultAgentState(),
		})
	}

	return (
		<div className="h-full w-full overflow-y-auto scrollbar-teal">
			<Guide />
			<div className="max-w-[1380px] mx-auto mt-8 flex flex-col p-4 relative">
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
				
				{/* Insights Page */}
				{insightClicked ? (
					<InsightsPage onClose={() => setInsightClicked(false)} />
				) : (
					<>
						
						{/* Pre-Launch */}
						{!launched && (
							<>
								{/* Repo Viewer, Issue Creator, and Agent Configs */}
								<div className="h-[75vh] flex gap-4 flex-1 overflow-hidden mt-[5vh]">
									<AnimatePresence>
										<motion.div 
											key="repo-panel"
											className="w-[30%] min-w-0 gap-4 flex items-stretch"
											exit={{ x: '-120%', opacity: 0 }}
											transition={{ duration: animationDuration, ease: "easeInOut"}}
										>
											<div className="flex-1">
												<RepoPreview />
											</div>
											<div className="w-[2px] bg-neon-teal/20 self-stretch" />
										</motion.div>
									</AnimatePresence>
									<div className={`${animComplete  ? 'w-full' : 'w-[70%]'} flex flex-col gap-4 overflow-hidde`}>	
										<AnimatePresence>
											<motion.div
												className="flex flex-col gap-4 flex-1 h-full overflow-hidden"
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

								{/* Buttons */}
								<div className="flex justify-end gap-6 mt-[3vh]">
									<button 
										onMouseDown={() => {
											setInsightClicked(true)
											setInsightHovered(false)
										}}
										onMouseEnter={() => setInsightHovered(true)}
										onMouseLeave={() => setInsightHovered(false)}
										className="w-64 flex items-center justify-center gap-2 font-space-mono font-bold text-sm tracking-widest uppercase py-3 rounded border border-neon-teal text-neon-teal hover:bg-neon-teal hover:text-black hover:scale-105 transition-all duration-200 cursor-pointer"
									>
										Arena Insights
										<img src={insightHovered ? insightsHoveredImg : insightsImg} alt="insights" className="w-3 h-3 object-contain" />
									</button>
									<button
										onClick={handleLaunch}
										className="w-64 font-space-mono font-bold text-sm tracking-widest uppercase py-3 rounded border border-neon-teal text-neon-teal hover:bg-neon-teal hover:text-black hover:scale-105 transition-all duration-200 cursor-pointer"
									>
										Launch Run →
									</button>
								</div>
							</>
						)}

						{/* Post-Launch */}
						{animComplete && (
							<div className="flex flex-col gap-10 mt-12">
								{/* Agent Cards */}
								<motion.div
									className="flex gap-8 w-full items-start"
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
											allFinished={allFinished}
											summary={agentState[config.version_id].summary}
										/>
									))}
								</motion.div>

								{/* Agent Tracks */}
								<motion.div
									className="flex gap-3 w-full mt-4"
									initial={{ opacity: 0 }}
									animate={{ opacity: 1 }}
									transition={{ duration: 0.5, delay: 0.2 }}
								>
									{agents.map((config, i) => (
										<div key={config.version_id} className="flex-1 flex flex-col items-center gap-2">
											<AgentTrack 
												agentNumber={i + 1}
												currentStep={agentState[config.version_id].step}
												artifacts={agentState[config.version_id].artifacts}
											/>
										</div>
									))}
								</motion.div>
								{allFinished && (
									<div className="flex justify-center">
										<button
											onClick={handleReset}
											className="w-64 item-center font-space-mono font-bold text-sm tracking-widest uppercase py-3 text-neon-teal hover:scale-105 transition-all duration-200 cursor-pointer"
										>
											← Back
										</button>
									</div>
								)}
							</div>
						)}		
					</>
				)}				
			</div>
		</div>
	)
}

export default App
