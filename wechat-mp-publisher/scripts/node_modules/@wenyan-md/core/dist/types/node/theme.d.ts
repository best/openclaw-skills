export interface ThemeOptions {
    list?: boolean;
    add?: boolean;
    name?: string;
    path?: string;
    rm?: string;
}
export interface ThemeInfo {
    id: string;
    name: string;
    description?: string;
    isBuiltin: boolean;
}
export declare function listThemes(): Promise<ThemeInfo[]>;
export declare function addTheme(name?: string, path?: string): Promise<void>;
export declare function removeTheme(name: string): Promise<void>;
