-- TI Panel skin script.

-- Double-clicking the LCD opens the patch browser, the same as pressing BROWSE.
function openBrowser()
  local browse = document:GetElementById("hwBrowse")
  if browse then
    browse:Click()
  end
end

-- Every pop-up's CLOSE button lands here: press the one button that shows "no page".
function closeOverlay()
  local close = document:GetElementById("hwCloseTab")
  if close then
    close:Click()
  end
end
