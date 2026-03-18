import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

/**
 * Capture a DOM element as PNG and trigger download.
 * Uses 2x scale for Retina quality.
 * @param element - DOM element to capture
 * @param filename - Download filename (without .png extension)
 */
export async function captureElementAsImage(
  element: HTMLElement,
  filename: string,
): Promise<void> {
  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: '#FFFFFF',
    useCORS: true,
    logging: false,
    windowWidth: element.scrollWidth,
    windowHeight: element.scrollHeight,
  })
  const link = document.createElement('a')
  link.download = `${filename}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}

/**
 * Capture a DOM element as a multi-page PDF (A4 portrait) and trigger download.
 * Content is paginated: if the element is taller than one A4 page, additional
 * pages are added automatically. No content is truncated.
 *
 * @param element - DOM element to capture
 * @param filename - Download filename (without .pdf extension)
 * @param title - Report title displayed at top of first page
 */
export async function captureElementAsPDF(
  element: HTMLElement,
  filename: string,
  title: string,
): Promise<void> {
  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: '#FFFFFF',
    useCORS: true,
    logging: false,
    windowWidth: element.scrollWidth,
    windowHeight: element.scrollHeight,
  })

  const pdf = new jsPDF('p', 'mm', 'a4')

  const pageWidth = pdf.internal.pageSize.getWidth()   // 210mm
  const pageHeight = pdf.internal.pageSize.getHeight() // 297mm
  const margin = 10
  const contentWidth = pageWidth - margin * 2

  // Title on first page
  pdf.setFontSize(11)
  pdf.setTextColor(60, 60, 60)
  pdf.text(title, margin, margin + 5)

  const titleAreaHeight = 14  // mm reserved for title

  // Calculate image dimensions to fit page width
  const imgWidthMm = contentWidth
  const imgHeightMm = (canvas.height / canvas.width) * imgWidthMm

  // Available content height per page (first page has title)
  const firstPageContentHeight = pageHeight - margin * 2 - titleAreaHeight
  const otherPageContentHeight = pageHeight - margin * 2

  // Convert mm to canvas pixel ratio for slicing
  // canvas pixel per mm = canvas.width / imgWidthMm
  const pxPerMm = canvas.width / imgWidthMm

  let remainingHeightMm = imgHeightMm
  let canvasOffsetPx = 0
  let isFirstPage = true

  while (remainingHeightMm > 0) {
    const availableHeightMm = isFirstPage ? firstPageContentHeight : otherPageContentHeight
    const sliceHeightMm = Math.min(remainingHeightMm, availableHeightMm)
    const sliceHeightPx = Math.round(sliceHeightMm * pxPerMm)

    // Create a temporary canvas for this page slice
    const sliceCanvas = document.createElement('canvas')
    sliceCanvas.width = canvas.width
    sliceCanvas.height = sliceHeightPx
    const ctx = sliceCanvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(
        canvas,
        0, canvasOffsetPx,                  // source x, y
        canvas.width, sliceHeightPx,        // source width, height
        0, 0,                               // dest x, y
        canvas.width, sliceHeightPx,        // dest width, height
      )
    }

    const sliceImgData = sliceCanvas.toDataURL('image/png')
    const yPos = isFirstPage ? margin + titleAreaHeight : margin

    pdf.addImage(sliceImgData, 'PNG', margin, yPos, imgWidthMm, sliceHeightMm)

    canvasOffsetPx += sliceHeightPx
    remainingHeightMm -= sliceHeightMm
    isFirstPage = false

    if (remainingHeightMm > 0.5) {  // 0.5mm tolerance to avoid blank trailing page
      pdf.addPage()
    }
  }

  pdf.save(`${filename}.pdf`)
}
