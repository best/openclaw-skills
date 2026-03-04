export interface MathJaxParserOptions {
    inlineMath?: [string, string][];
    displayMath?: [string, string][];
    fontCache?: "none" | "local" | "global";
}
export declare function createMathJaxParser(options?: MathJaxParserOptions): {
    parser(htmlString: string): string;
};
