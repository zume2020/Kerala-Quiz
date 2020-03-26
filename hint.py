import random

def hintGen(answer):
    hint = []

    len_ans= len(answer)

    if 0 <= len_ans <= 4:
        h_min = 1
        h_max = 2
    elif 4 <= len_ans <= 8:
        h_min = 2
        h_max = 3
    elif 8 <= len_ans <= 12:
        h_min = 3
        h_max = 5
    elif 12 <= len_ans <= 16:
        h_min = 4
        h_max = 8
    else:
        h_min = 5
        h_max = 12

    _hint = ''
    nums = [x for x in range(len(answer))]
    random.shuffle(nums)

    for x in range(len(answer)):

        if answer[x] != ' ':
            _hint += '_ '
        else:
            _hint += '  '
    hint.append(_hint)

    _hint = ''

    for x in range(len(answer)):
        if x in nums[:h_min]:
            if answer[x] != ' ':
                _hint += answer[x] + ' '
            else:
                _hint += '  '
        else:
            if answer[x] != ' ':
                _hint += '_ '
            else:
                _hint += '  '

    hint.append(_hint)

    _hint = ''
    for x in range(len(answer)):
        if x in nums[:h_max]:
            if answer[x] != ' ':
                _hint += answer[x] + ' '
            else:
                _hint += '  '
        else:
            
            if answer[x] != ' ':
                _hint += '_ '
            else:
                _hint += '  '

    hint.append(_hint)

    return hint