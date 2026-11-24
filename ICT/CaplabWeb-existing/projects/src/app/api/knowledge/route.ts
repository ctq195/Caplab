import { NextRequest, NextResponse } from 'next/server';

/**
 * 知识库问答 API - 基于 CapLab 免费版知识库 v2.3.0 进行检索和回答
 * 覆盖考研、考公/选调、境外升学、求职实习的规则、时间线与要求
 */

// 模拟知识库数据（实际项目中会从 JSON 卡片或数据库检索）
const KNOWLEDGE_BASE = [
  {
    id: 'KB001',
    category: '考研',
    title: '考研报名时间与流程',
    content:
      '全国硕士研究生招生考试一般在每年 10 月网上报名，12 月下旬初试。报名前需确认报考资格、选择招生单位和专业。',
    source: '教育部官网',
    verifiedDate: '2026-09-01',
    status: 'verified',
  },
  {
    id: 'KB002',
    category: '考公',
    title: '国考与省考时间线',
    content:
      '国家公务员考试一般 10 月报名、11-12 月笔试。各省省考时间不一，多数在上半年（3-4 月）进行。应届生可关注选调生项目。',
    source: '国家公务员局',
    verifiedDate: '2026-08-15',
    status: 'verified',
  },
  {
    id: 'KB003',
    category: '留学',
    title: '境外升学申请时间线',
    content:
      '多数国家/地区秋季入学申请在前一年 9-12 月截止（部分滚动录取）。需提前准备语言成绩（托福/雅思）、推荐信、个人陈述。',
    source: '各院校官网汇总',
    verifiedDate: '2026-07-20',
    status: 'verified',
  },
  {
    id: 'KB004',
    category: '求职',
    title: '秋招与春招节奏',
    content:
      '秋招一般 8-10 月启动（互联网大厂更早），春招 2-4 月补录。实习转正通常在实习结束前 1-2 个月评估。',
    source: '行业调研',
    verifiedDate: '2026-06-10',
    status: 'verified',
  },
  {
    id: 'KB005',
    category: '求职',
    title: '产品实习常见要求',
    content:
      '产品实习通常要求：沟通能力、需求分析能力、原型工具（Axure/Figma）基础、对互联网产品有热情。有产品项目经历优先。',
    source: '岗位 JD 汇总',
    verifiedDate: '2026-05-15',
    status: 'verified',
  },
];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query, category } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: '查询内容不能为空' },
        { status: 400 }
      );
    }

    // 简单的关键词匹配检索（实际项目中会用向量检索或全文搜索）
    const queryLower = query.toLowerCase();
    let results = KNOWLEDGE_BASE.filter((item) => {
      const matchQuery =
        item.title.toLowerCase().includes(queryLower) ||
        item.content.toLowerCase().includes(queryLower) ||
        item.category.toLowerCase().includes(queryLower);
      const matchCategory = !category || item.category === category;
      return matchQuery && matchCategory;
    });

    // 如果没有精确匹配，返回所有条目（演示用）
    if (results.length === 0) {
      results = KNOWLEDGE_BASE.slice(0, 3);
    }

    // 生成回答
    const answer =
      results.length > 0
        ? `根据知识库检索，找到 ${results.length} 条相关信息：\n\n${results
            .map(
              (r, i) =>
                `${i + 1}. **${r.title}**（${r.category}）\n   ${r.content}\n   来源：${r.source} · 核验日期：${r.verifiedDate}`
            )
            .join('\n\n')}\n\n⚠️ 动态信息（报名/考试/岗位/费用/截止）请以官方最新公告为准。`
        : '未找到相关信息。建议直接访问官方网站查询最新动态。';

    // 模拟检索延迟
    await new Promise((resolve) => setTimeout(resolve, 200));

    return NextResponse.json({
      success: true,
      data: {
        answer,
        results: results.map((r) => ({
          id: r.id,
          title: r.title,
          category: r.category,
          source: r.source,
          verifiedDate: r.verifiedDate,
          status: r.status,
        })),
        metadata: {
          knowledgeBaseVersion: '免费版 v2.3.0',
          retrievalMode: 'keyword_match',
          totalResults: results.length,
        },
      },
    });
  } catch (error) {
    console.error('Knowledge API error:', error);
    return NextResponse.json(
      { error: '知识库检索失败，请重试' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    success: true,
    data: {
      name: 'CapLab 知识库 API',
      version: '免费版 v2.3.0',
      categories: ['考研', '考公', '留学', '求职'],
      totalDocuments: KNOWLEDGE_BASE.length,
    },
  });
}
