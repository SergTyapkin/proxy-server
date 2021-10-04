def str_between(string, start, end, replace_to=None):
    end_idx = start_idx = string.find(start) + len(start)
    if isinstance(end, list):
        while string[end_idx] not in end and end_idx < len(string):
            end_idx += 1
    else:
        end_idx = string.find(end)

    if replace_to is not None:
        return string[:start_idx] + replace_to + string[end_idx:]
    else:
        return string[start_idx: end_idx], start_idx, end_idx
