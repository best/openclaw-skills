export interface FrontMatterResult {
    body: string;
    title?: string;
    cover?: string;
    description?: string;
    author?: string;
    source_url?: string;
}
export declare function handleFrontMatter(markdown: string): Promise<FrontMatterResult>;
