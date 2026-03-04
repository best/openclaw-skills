import * as csstree from "css-tree";
type CssUpdate = {
    property: string;
    value?: string;
    append?: boolean;
};
export type CssUpdateMap = Record<string, CssUpdate[]>;
export declare const parseOptions: csstree.ParseOptions;
export declare function createCssModifier(updates: CssUpdateMap): (customCss: string) => string;
export declare function createCssApplier(css: string): (element: HTMLElement) => void;
export {};
