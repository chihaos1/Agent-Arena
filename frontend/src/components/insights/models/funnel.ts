export interface FunnelStep {
    custom_name: string
    order: number
    count: number
    breakdown_value: string[]
}

export interface FunnelData {
    result: FunnelStep[][]
}