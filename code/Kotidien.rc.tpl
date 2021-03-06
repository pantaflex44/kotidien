VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={version_tuple},
        prodvers={version_tuple},
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date={date_tuple}
        ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    u'040904B0',
                    [StringStruct(u'CompanyName', u'{author}'),
                     StringStruct(u'FileDescription', u'{description}'),
                     StringStruct(u'FileVersion', u'{version}'),
                     StringStruct(u'InternalName', u'{name}'),
                     StringStruct(u'LegalCopyright', u'{copyright}'),
                     StringStruct(u'OriginalFilename', u'{exe}'),
                     StringStruct(u'ProductName', u'{name}'),
                     StringStruct(u'ProductVersion', u'{version}')])
                    ]),
                    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
                    ]
                    )
