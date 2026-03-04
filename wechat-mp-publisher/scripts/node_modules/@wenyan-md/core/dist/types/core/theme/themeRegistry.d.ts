export interface ThemeMeta {
    id: string;
    name: string;
    description: string;
    appName: string;
    author: string;
}
export interface Theme {
    meta: ThemeMeta;
    getCss(): Promise<string>;
}
export declare function registerTheme(theme: Theme): void;
export declare function getTheme(id: string): Theme | undefined;
export declare function getAllThemes(): Theme[];
export declare function registerAllBuiltInThemes(): void;
export declare function getAllGzhThemes(): Theme[];
