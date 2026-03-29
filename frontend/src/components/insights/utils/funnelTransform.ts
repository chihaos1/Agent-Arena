import { type FunnelStep } from '../models/funnel'
import { type Node, type Edge } from "@xyflow/react"

const STEP_GAP = 280
const SUCCESS_Y = 0
const DROPPED_Y = 130

export function buildFlowData(steps: FunnelStep[]) {
    const nodes: Node[] = []
    const edges: Edge[] = []
    const maxCount = steps[0].count

    steps.forEach((step, i) => {
        const x = i * STEP_GAP
        const nodeId = `step-${i}`
        
        // Success node
        nodes.push({
            id: nodeId, 
            type: 'funnel',
            position: { x, y: SUCCESS_Y },
            data: {
                label: step.custom_name,
                count: step.count,
                isDrop: false,
                conversion: Math.round((step.count / maxCount) * 100)
            }
        })

        if (i < steps.length - 1) {
            const next = steps[i + 1]
            const dropped = step.count - next.count

            // Success edge — variable width
            edges.push({
                id: `edge-${i}`,
                source: nodeId,
                target: `step-${i + 1}`,
                animated: true,
                style: {
                    stroke: '#73f8ce',
                    strokeWidth: Math.max((next.count / maxCount) * 20, 2),
                    opacity: 0.5
                }
            })

            if (dropped > 0) {
                const dropId = `drop-${i}`
                nodes.push({
                    id: dropId,
                    type: 'funnel',
                    position: { x: x + 120, y: DROPPED_Y },
                    data: { label: 'Failed', count: dropped, isDrop: true }
                })

                edges.push({
                    id: `drop-edge-${i}`,
                    source: nodeId,
                    target: dropId,
                    style: {
                        stroke: '#ef4444',
                        strokeWidth: Math.max((dropped / maxCount) * 15, 1),
                        strokeDasharray: '5 5'
                    }
                })
            }
        }
    })
    return { nodes, edges }
}