import { ApplyStylesOptions } from "../core/index.js";
import { GetInputContentFn, RenderContext, RenderOptions, StyledContent } from "./types.js";
export declare function renderWithTheme(markdownContent: string, options: RenderOptions): Promise<StyledContent>;
export declare function renderStyledContent(content: string, options?: ApplyStylesOptions): Promise<StyledContent>;
export declare function prepareRenderContext(inputContent: string | undefined, options: RenderOptions, getInputContent: GetInputContentFn): Promise<RenderContext>;
