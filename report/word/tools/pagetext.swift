import PDFKit
import Foundation
let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
var pages: [String] = []
for i in 0..<doc.pageCount { pages.append(doc.page(at: i)?.string ?? "") }
let data = try! JSONSerialization.data(withJSONObject: pages)
FileManager.default.createFile(atPath: CommandLine.arguments[2], contents: data)
print("pages", doc.pageCount)
