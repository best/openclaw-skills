export declare const serif = "Georgia, Cambria, 'Noto Serif', 'Times New Roman', serif";
export declare const sansSerif = "system-ui, 'Apple Color Emoji', 'Segoe UI', 'Segoe UI Symbol', 'Noto Sans', 'Roboto', sans-serif";
export declare const monospace = "Menlo, Monaco, Consolas, 'Liberation Mono', 'Roboto Mono', 'Courier New', 'Microsoft YaHei', monospace";
export declare function normalizeCssLoader(loaderOrContent: any): () => Promise<string>;
export declare function stringToMap(str: string): Map<string, string>;
export declare function replaceCSSVariables(css: string): string;
export declare function resolveCssContent<T extends {
    getCss: () => Promise<string>;
}>(directCss: string | undefined, // 直接传入的 CSS
id: string, // ID
finder: (id: string) => T | undefined, // 精确查找函数 (getTheme)
fallbackFinder: (id: string) => T | undefined, // 模糊查找函数 (find in array)
errorMessage: string): Promise<string>;
export type CssSource = {
    type: "inline";
    css: string;
} | {
    type: "asset";
    loader: () => Promise<string>;
} | {
    type: "url";
    url: string;
};
export declare function loadCssBySource(source: CssSource): Promise<string>;
