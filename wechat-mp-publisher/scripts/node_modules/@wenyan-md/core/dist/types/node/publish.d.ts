import { WechatPublishResponse } from "../wechat.js";
export interface WechatPublishOptions {
    appId?: string;
    appSecret?: string;
    relativePath?: string;
}
export interface ArticleOptions {
    title: string;
    content: string;
    cover?: string;
    author?: string;
    source_url?: string;
}
export declare function publishToWechatDraft(articleOptions: ArticleOptions, publishOptions?: WechatPublishOptions): Promise<WechatPublishResponse>;
export declare function publishToDraft(title: string, content: string, cover?: string, options?: WechatPublishOptions): Promise<WechatPublishResponse>;
