import { useEffect, useState } from 'react'

interface TreeItem {
    path: string;
    type: "blob" | "tree"
}

interface RepoData {
    name: string; 
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

function TreeView({ nodes, prefix = ""}: { nodes: TreeNodes; prefix?: string }) {
    const nodeArray = Object.values(nodes);

    return (
        <>
            {
                nodeArray.map((node, i) => {
                    const isLast = i === nodeArray.length -1
                    const connector = isLast ? '└── ' : '├── '

                    return (
                        <div>
                            
                        </div>
                    )
                })
            }
        </>
    )
}