import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

/**
 * Capture a DOM element as PNG and trigger download.
 * @param element - DOM element to capture
 * @param filename - Download filename (without extension)
 */
export async function captureElementAsImage(
  element: HTMLElement,
  filename: string
): Promise<void> {
  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: '#FFFFFF',
    useCORS: true,
    logging: false,
  })
  const link = document.createElement('a')
  link.download = `${filename}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}

/**
 * Capture a DOM element as PDF (A4 portrait) and trigger download.
 * Title line at top: "MiroFishmoody 推演报告 — {campaignName} — {date}"
 * Content is the captured element fitted to A4 width with margins.
 * @param element - DOM element to capture
 * @param filename - Download filename (without extension)
 * @param title - Report title line
 */
export async function captureElementAsPDF(
  element: HTMLElement,
  filename: string,
  title: string
): Promise<void> {
  const canvas = await html2canvas(element, {
    scale: 2,
    backgroundColor: '#FFFFFF',
    useCORS: true,
    logging: false,
  })
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF('p', 'mm', 'a4')
  const pageWidth = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const margin = 10
  const contentWidth = pageWidth - margin * 2

  // Title
  pdf.setFontSize(12)
  pdf.text(title, margin, margin + 5)

  // Image below title
  const titleHeight = 15
  const imgWidth = contentWidth
  const imgHeight = (canvas.height / canvas.width) * imgWidth
  const availableHeight = pageHeight - margin * 2 - titleHeight

  // If image is taller than one page, scale to fit
  const finalHeight = Math.min(imgHeight, availableHeight)
  const finalWidth = imgHeight > availableHeight
    ? (canvas.width / canvas.height) * finalHeight
    : imgWidth

  pdf.addImage(imgData, 'PNG', margin, margin + titleHeight, finalWidth, finalHeight)
  pdf.save(`${filename}.pdf`)
}
