set rtp+=webapi-vim

function! VisualSelection()
    if mode()=="v"
        let [line_start, column_start] = getpos("v")[1:2]
        let [line_end, column_end] = getpos(".")[1:2]
    else
        let [line_start, column_start] = getpos("'<")[1:2]
        let [line_end, column_end] = getpos("'>")[1:2]
    end
    if (line2byte(line_start)+column_start) > (line2byte(line_end)+column_end)
        let [line_start, column_start, line_end, column_end] =
        \   [line_end, column_end, line_start, column_start]
    end
    let lines = getline(line_start, line_end)
    if len(lines) == 0
            return ''
    endif
    let lines[-1] = lines[-1][: column_end - 1]
    let lines[0] = lines[0][column_start - 1:]
    return join(lines, "\n")
endfunction

function! pyeye#ExecuteVisual() abort
  let url = 'http://localhost:8080'
  let payload = webapi#json#encode({'code': VisualSelection()})
  let ret = webapi#http#post(url, payload, {'Content-Type': 'application/json'})
endfunction

:vnoremap <F5> :<C-u>call pyeye#ExecuteVisual()<CR>
:nnoremap <F5> <S-v>:<C-u>call pyeye#ExecuteVisual()<CR><Esc>
:nnoremap <S-F5> {j<S-v>}k:<C-u>call pyeye#ExecuteVisual()<CR><Esc>
