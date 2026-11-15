on run argv
  set inPath to item 1 of argv
  set outPath to item 2 of argv
  tell application id "com.apple.iWork.Pages"
    activate
    open (POSIX file inPath as alias)
    repeat 60 times
      if (count of documents) > 0 then exit repeat
      delay 1
    end repeat
    delay 2
    set d to front document
    export d to (POSIX file outPath) as PDF
    close d saving no
  end tell
end run
