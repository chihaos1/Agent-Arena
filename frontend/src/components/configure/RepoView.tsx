import { useEffect, useState } from 'react'

interface TreeItem {
    path: string;
    type: "blob" | "tree"
}

interface RepoData {
    name: string; 
    html_url: string;
    description: string; 
    stargazers_count: number; 
    forks_count: number; 
    open_issues_count: number 
}

type TreeNode = {
  name: string;
  type: 'blob' | 'tree';
  children: TreeNodes;
}

type TreeNodes = Record<string, TreeNode>;

function buildTree(items: TreeItem[]): TreeNodes {
    return items.reduce<TreeNodes>((root, item) => {
        const parts = item.path.split('/');
        let currentLevel = root;

        parts.forEach((part, i) => {
            const isLast = i === parts.length - 1;
            if (!currentLevel[part]) {
                currentLevel[part] = { name: part, type: isLast ? item.type : 'tree', children: {} };
            }
            currentLevel = currentLevel[part].children;
        })
        return root;
    }, {})
}

function TreeView({ nodes, depth = 0 }: { nodes: TreeNodes; depth?: number }) {
    const nodeArray = Object.values(nodes);

    return (
        <>
            {
                nodeArray.map((node, i) => {
                    const isLast = i === nodeArray.length - 1;

                    return (
                        <div 
                            key={`${depth}-${node.name}`}
                            className="relative"
                            style={{ marginLeft: depth === 0 ? 0 : 16 }}
                        >
                            <div className="flex items-center">
                                {
                                    depth > 0 && (
                                    <>
                                        {/* vertical line */}
                                        {!isLast && ( 
                                            <div className="absolute border-l-2 border-neon-teal" style={{ left: -12, top: 0, bottom: 0 }} />
                                        )}
                                        {/* elbow */}
                                        <div className="absolute border-l-2 border-b-2 border-neon-teal rounded-bl-sm" style={{ left: -12, top: 0, width: 10, height: 12 }} />
                                    </>
                                    )
                                }
                                <span className={node.type === 'tree' ? 'text-neon-teal font-bold' : 'text-gray-200'}>
                                    {node.type === 'tree' ? '📁' : '📄'} {node.name}
                                </span>
                            </div>
                            {node.type === "tree" && (
                                <TreeView nodes={node.children} depth={depth + 1}/>
                            )} 
                        </div>
                    )
                })
            }
        </>
    )
}

export default function RepoPreview() {
    
    const [repo, setRepo] = useState<RepoData | null>(null)
    const [tree, setTree] = useState<TreeItem[]>([])
    const [error, setError] = useState<string | null>(null)
    
    useEffect(() => {
        const load = async () => {
            try {
                const response = await fetch("http://127.0.0.1:8000/repo/repo-preview")

                if (!response.ok) throw new Error("Failed to fetch data")

                const data = await response.json()
                setRepo(data.repo)
                setTree(data.tree)

            } catch (error) {
                console.error("Tree Fetch Error:", error)
                setError("Failed to load repository")
            }
        }
        load()
    }, [])

    if (error) return <div className="text-red-400 p-4">{error}</div>
    if (!repo) return (
        <div className="h-[75vh] flex items-center justify-center bg-neon-purple rounded-lg border-2 border-neon-teal/30 font-space-mono text-neon-teal font-bold">
            Loading...
        </div>
    )

    return (
        <div className="h-[75vh] flex flex-col items-center bg-neon-purple rounded-lg border-2 border-neon-teal/30 p-4 font-space-mono overflow-hidden">
            <div className="mb-4">
                <h2 className="text-xl font-semibold text-white">
                    <a href={repo.html_url} target="_blank" rel="noopener noreferrer" className="hover:text-neon-teal transition-colors">
                        {repo.name}    
                    </a>
                </h2>
                <p className="text-gray-350 text-xs mt-2">{repo.description}</p>
                <div className="flex justify-around mt-2 text-xs">
                    <span>⭐ {repo.stargazers_count}</span>
                    <span>🍴 {repo.forks_count}</span>
                    <span>🐛 {repo.open_issues_count}</span>
                </div>
            </div>
            <div className="overflow-y-auto flex-1 scrollbar-teal">
                <TreeView nodes={buildTree(tree)} />
            </div>
        </div>
    )
}