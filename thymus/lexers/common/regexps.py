PREFIX_LEN = r'(?:/\d{1,3})?'

IPV6_LINK_LOCAL = r'fe80:(?::[a-f0-9]{1,4}){0,4}%[0-9a-z]+' + PREFIX_LEN
IPV6_V4_EMBEDDED = r'(?:[a-f0-9]{1,4}:){1,4}:(?:\d{1,3}\.){3}\d{1,3}' + PREFIX_LEN
IPV6_V4_MAPPED = r'::(?:ffff:(?:0:)?)?(?:\d{1,3}\.){3}\d{1,3}' + PREFIX_LEN
IPV6_ADDR_1 = r'(?:[a-f0-9]{1,4}:){7}[a-f0-9]{1,4}' + PREFIX_LEN
IPV6_ADDR_2 = r'(?:[a-z0-9]{1,4}:){1,6}:[a-z0-9]{1,4}' + PREFIX_LEN
IPV6_ADDR_3 = r'(?:[a-z0-9]{1,4}:){1,5}(?:[a-f0-9]{1,4}){1,2}' + PREFIX_LEN
IPV6_ADDR_4 = r'(?:[a-z0-9]{1,4}:){1,4}(?:[a-f0-9]{1,4}){1,3}' + PREFIX_LEN
IPV6_ADDR_5 = r'(?:[a-z0-9]{1,4}:){1,3}(?:[a-f0-9]{1,4}){1,4}' + PREFIX_LEN
IPV6_ADDR_6 = r'(?:[a-z0-9]{1,4}:){1,2}(?:[a-f0-9]{1,4}){1,5}' + PREFIX_LEN
IPV6_ADDR_7 = r'[a-f0-9]{1,4}:(?::[a-f0-9]{1,4}){1,6}' + PREFIX_LEN
IPV6_ADDR_8 = r'(?:(?::[a-f0-9]{1,4}){1,7}|:)' + PREFIX_LEN
IPV6_ADDR_9 = r'(?:[0-9a-f]{1,4}:){1,7}:' + PREFIX_LEN

IPV6_REGEXP = f'{IPV6_LINK_LOCAL}|{IPV6_V4_EMBEDDED}|{IPV6_V4_MAPPED}|{IPV6_ADDR_1}|{IPV6_ADDR_2}|{IPV6_ADDR_3}'
IPV6_REGEXP += f'|{IPV6_ADDR_4}|{IPV6_ADDR_5}|{IPV6_ADDR_6}|{IPV6_ADDR_7}|{IPV6_ADDR_8}|{IPV6_ADDR_9}'

IPV4_REGEXP = r'(?:\d{1,3}\.){3}\d{1,3}' + PREFIX_LEN  # SIMPLE ENOUGH
