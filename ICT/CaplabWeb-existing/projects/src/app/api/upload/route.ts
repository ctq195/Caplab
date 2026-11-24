import { NextRequest, NextResponse } from 'next/server';

/**
 * 文件上传 API - 处理简历、成绩单等材料的上传
 * 支持 PDF、Word、图片格式
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File | null;

    if (!file) {
      return NextResponse.json(
        { error: '请选择要上传的文件' },
        { status: 400 }
      );
    }

    // 验证文件类型
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/jpeg',
      'image/png',
      'image/webp',
    ];

    if (!allowedTypes.includes(file.type)) {
      return NextResponse.json(
        { error: '不支持的文件格式，请上传 PDF、Word 或图片' },
        { status: 400 }
      );
    }

    // 验证文件大小（10MB）
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: '文件大小不能超过 10MB' },
        { status: 400 }
      );
    }

    // 模拟文件处理（实际项目中这里会调用 OCR 或文档解析服务）
    const fileId = `file-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    // 根据文件类型返回不同的处理结果
    const isImage = file.type.startsWith('image/');
    const extractResult = isImage
      ? {
          status: 'ocr_pending',
          message: '图片识别结果仅供参考，关键信息请手动确认后再写入档案。',
          extractedFields: [],
        }
      : {
          status: 'parsed',
          message: '文件已解析，请确认以下提取的信息是否准确。',
          extractedFields: [
            { field: '专业', value: '计算机科学与技术', confidence: 'high' },
            { field: '年级', value: '大三', confidence: 'high' },
            { field: '预计毕业', value: '2027-06', confidence: 'medium' },
          ],
        };

    // 模拟处理延迟
    await new Promise((resolve) => setTimeout(resolve, 500));

    return NextResponse.json({
      success: true,
      data: {
        fileId,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        ...extractResult,
        uploadedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error('Upload API error:', error);
    return NextResponse.json(
      { error: '文件上传失败，请重试' },
      { status: 500 }
    );
  }
}
