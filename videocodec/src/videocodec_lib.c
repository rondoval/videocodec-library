/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * videocodec_lib.c - resident, library init/open/close/expunge.
 *
 * Backends are opened at the first call that needs one (not here: the
 * drawer scan takes DOS, which only a Process may call) and closed at the
 * expunge.
 */
#include <exec/memory.h>
#include <exec/resident.h>

#include <minlist.h>

#include <videocodec_private.h>

LONG __attribute__((used, section(".text.entry"))) doNotExecute(void);
/**
 * doNotExecute() - The file's first code: run as a program, it returns at once.
 *
 *
 * Return: -1.
 */
LONG __attribute__((used, section(".text.entry"))) doNotExecute(void)
{
	return -1;
}

extern const UBYTE endOfCode;
static const char libraryName[] = LIBRARY_NAME;
static const char libraryIdString[] = LIBRARY_IDSTRING;
static const APTR initTable[4];

const struct Resident videocodecResident __attribute__((used, section(".text.modhdr"))) = {
    RTC_MATCHWORD,
    (struct Resident *)&videocodecResident,
    (APTR)&endOfCode,
    RTF_AUTOINIT,
    LIBRARY_VERSION,
    NT_LIBRARY,
    LIBRARY_PRIORITY,
    (APTR)&libraryName,
    (APTR)&libraryIdString,
    (APTR)initTable,
};

/**
 * lib_free() - Free the library base's memory (the function table below it included).
 * @base: the library base, no longer in the system's list
 */
static void lib_free(struct VideoCodecBase *base)
{
	struct ExecBase *SysBase = base->SysBase;
	FreeMem((APTR)((ULONG)base - base->lib.lib_NegSize), (ULONG)base->lib.lib_NegSize + base->lib.lib_PosSize);
}

/**
 * LibExpunge() - Library expunge entry: free the library when nothing holds it, else flag it for deletion.
 *
 * @base: the library base (register a6)
 *
 * Return: the segment list for the loader to unload, 0 when the expunge is deferred.
 */
static ULONG LibExpunge(struct VideoCodecBase *base asm("a6"))
{
	struct ExecBase *SysBase = base->SysBase;
	ULONG segList = base->segList;

	if (base->lib.lib_OpenCnt > 0)
	{
		base->lib.lib_Flags |= LIBF_DELEXP;
		return 0;
	}
	vc_backends_free(base);
	CloseLibrary(base->UtilityBase);

	Forbid();
	Remove((struct Node *)base);
	Permit();

	lib_free(base);
	return segList;
}

/**
 * LibInit() - Library init entry (RTF_AUTOINIT): set the base up and open what the library uses.
 *
 * @lib: the library base the loader built (register d0)
 * @seglist: the library's segment list (register a0)
 * @SysBase: exec.library's base (register a6)
 *
 * Return: the library base, NULL when something could not be opened (the base is freed).
 */
static struct Library *LibInit(struct Library *lib asm("d0"), ULONG seglist asm("a0"), struct ExecBase *SysBase asm("a6"))
{
	struct VideoCodecBase *base = (struct VideoCodecBase *)lib;

	base->segList = seglist;
	base->SysBase = SysBase;
	base->lib.lib_Revision = (UWORD)LIBRARY_REVISION;
	/* tag lists: without them the library does not come up */
	base->UtilityBase = OpenLibrary((CONST_STRPTR) "utility.library", 36);
	if (base->UtilityBase == NULL)
	{
		lib_free(base);
		return NULL;
	}
	InitSemaphore(&base->lock);
	vc_backends_init(base);
	return lib;
}

/**
 * LibOpen() - Library open entry: count the opener and cancel a pending expunge.
 *
 * @version: the version asked for (register d0), not checked
 * @base: the library base (register a6)
 *
 * Return: the library base.
 */
static struct VideoCodecBase *LibOpen(ULONG version asm("d0"), struct VideoCodecBase *base asm("a6"))
{
	(void)version;
	base->lib.lib_OpenCnt++;
	base->lib.lib_Flags &= (UBYTE)~LIBF_DELEXP;
	return base;
}

/**
 * LibClose() - Library close entry: drop an opener, expunge when it was the last and an expunge is pending.
 *
 * @base: the library base (register a6)
 *
 * Return: the segment list when the library was expunged, else 0.
 */
static ULONG LibClose(struct VideoCodecBase *base asm("a6"))
{
	base->lib.lib_OpenCnt--;
	if (base->lib.lib_OpenCnt == 0)
		vc_backends_idle(base); /* in the closing task: a backend may wait for its hardware, which the expunge must not */
	if (base->lib.lib_OpenCnt == 0 && (base->lib.lib_Flags & LIBF_DELEXP))
		return LibExpunge(base);
	return 0;
}

/**
 * LibNull() - The reserved library slot, which AmigaOS never calls: 'do not execute'.
 *
 *
 * Return: 0.
 */
static ULONG LibNull(void)
{
	return 0;
}

static const APTR funcTable[] = {
    (APTR)LibOpen,
    (APTR)LibClose,
    (APTR)LibExpunge,
    (APTR)LibNull,
    (APTR)VC_OpenSessionTagList,
    (APTR)VC_CloseSession,
    (APTR)VC_ImportPacket,
    (APTR)VC_ImportFrame,
    (APTR)VC_SendPacket,
    (APTR)VC_SendFrame,
    (APTR)VC_Poll,
    (APTR)VC_ReleaseFrame,
    (APTR)VC_ReleasePacket,
    (APTR)VC_Flush,
    (APTR)VC_SetAttrsTagList,
    (APTR)VC_QueryCodec,
    (APTR)VC_GetBackendInfo,
    (APTR)VC_DecodeImageTagList,
    (APTR)VC_EncodeImageTagList,
    (APTR)VC_ConvertImageTagList,
    (APTR)VC_GetImageInfo,
    (APTR)VC_CodecOfTag,
    (APTR)-1,
};

static const APTR initTable[4] = {
    (APTR)sizeof(struct VideoCodecBase),
    (APTR)funcTable,
    NULL,
    (APTR)LibInit,
};
