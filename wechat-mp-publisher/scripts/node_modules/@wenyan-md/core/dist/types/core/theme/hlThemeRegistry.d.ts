export interface HlTheme {
    id: string;
    getCss(): Promise<string>;
}
export declare function registerHlTheme(theme: HlTheme): void;
export declare function getHlTheme(id: string): HlTheme | undefined;
export declare function getAllHlThemes(): HlTheme[];
export declare function registerBuiltInHlThemes(): void;
