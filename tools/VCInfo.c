/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * VCInfo - whether the video libraries are set up, and what they can do: the
 * check to run after installing them, and what a bug report needs.
 *
 *   VCInfo                            the setup in plain words, each part OK
 *                                     or a failure with its cure:
 *                                     videocodec.library, each codec driver
 *                                     with its codecs and codec memory, a
 *                                     session of each opened and closed, and
 *                                     with vcjpeg.datatype installed, whether
 *                                     its descriptor comes first for JPEGs
 *   VCInfo CODECS                     what the codec drivers do: codec, kind,
 *                                     limits, the pixel formats it writes
 *                                     and reads, and whether a
 *                                     session or an image call serves it
 *   VCInfo COUNTERS                   every codec driver's state and counters
 *
 * The link to the VideoCore under videocore.codec, vchiq.device, is the Emu68
 * driver stack's, and VCHIQInfo checks it: VCInfo sends you there when the
 * VideoCore does not answer.
 *
 * One command per run; each ends with PASS or FAIL.
 *
 * Hosted CLI program (libnix): videocodec.library's calls only.
 *
 * Return codes: 0 PASS, 5 PASS with warnings, 10 a part is not installed,
 * 20 failed.
 */
#ifdef __INTELLISENSE__
#include <clib/exec_protos.h>
#include <clib/dos_protos.h>
#include <clib/datatypes_protos.h>
#include <clib/videocodec_protos.h>
#else
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/datatypes.h>
#include <proto/videocodec.h>
#endif

#include <exec/types.h>
#include <datatypes/datatypes.h>
#include <datatypes/datatypesclass.h>
#include <dos/dos.h>
#include <dos/rdargs.h>

#include <string.h>

#include <bits.h>
#include <strutil.h>
#include <libraries/videocodec.h>

#include "vc_names.h"

struct Library *VideoCodecBase;
struct Library *DataTypesBase;

static const char verstag[] __attribute__((used)) = VERSTAG;

#define DRIVER_COUNTERS 16 /* the counters COUNTERS asks a codec driver for */

/* ---- COUNTERS ---------------------------------------------------------------- */

/**
 * do_counters() - COUNTERS: every codec driver's state and counters, and its codec memory.
 *
 * Return: RETURN_OK, RETURN_FAIL if there are no codec drivers.
 */
static int do_counters(void)
{
	ULONG drivers = 0;
	for (;; drivers++)
	{
		struct VCCounter counters[DRIVER_COUNTERS];
		struct VCInfo vi;
		vi.Size = sizeof(vi);
		vi.Counters = counters;
		vi.MaxCounters = ARRAY_SIZE(counters);
		if (VC_GetBackendInfo(drivers, &vi) != 0)
			break;
		Printf((CONST_STRPTR) "%s: ABI %ld.%ld, %ld codecs, %ld sessions", vi.Backend, vi.ABIVersion >> 16,
		    vi.ABIVersion & 0xffffu, vi.Codecs, vi.Sessions);
		if (vi.Interface[0] != 0)
			Printf((CONST_STRPTR) ", %s", vi.Interface);
		for (ULONG k = 0; k < vi.NumCounters && k < vi.MaxCounters; k++)
			Printf((CONST_STRPTR) "%s%s %ld", k == 0 ? "; " : ", ", counters[k].Name, counters[k].Value);
		Printf((CONST_STRPTR) "\n");
		if (VC_HAS_FIELD(vi.Size, struct VCInfo, MemFree) && vi.MemTotal != 0)
			Printf((CONST_STRPTR) "%s: codec memory %ld MiB free of %ld MiB\n", vi.Backend, vi.MemFree >> 20,
			    vi.MemTotal >> 20);
	}
	return drivers != 0 ? RETURN_OK : RETURN_FAIL;
}

/* ---- CODECS ------------------------------------------------------------------ */

/**
 * formats_print() - One list of a codec row's formats: "; <what> <names>".
 * @what:    what the row does with them: "writes", "reads"
 * @formats: VCF_MASK()s; nothing is printed for 0
 */
static void formats_print(const char *what, ULONG formats)
{
	if (formats == 0)
		return;
	Printf((CONST_STRPTR) "; %s", what);
	for (ULONG f = 0; f < FORMAT_BITS; f++)
		if (formats & VCF_MASK(f))
			Printf((CONST_STRPTR) " %s", format_name(f));
}

/**
 * do_codecs() - CODECS: every codec driver's codec rows.
 *
 * Return: RETURN_OK, RETURN_FAIL if there are none.
 */
static int do_codecs(void)
{
	ULONG n = 0;
	for (ULONG i = 0;; i++)
	{
		struct VCCodecInfo ci;
		ci.Size = sizeof(ci);
		if (VC_QueryCodec(i, &ci) != 0)
			break;
		char tag[TAG_NAME_SIZE];
		Printf((CONST_STRPTR) "  %s", codec_name(ci.Codec));
		if (VC_HAS_FIELD(ci.Size, struct VCCodecInfo, Tag) && ci.Tag != 0)
			Printf((CONST_STRPTR) " (%s)", tag_name(ci.Tag, tag));
		Printf((CONST_STRPTR) " %s: up to %ldx%ld", kind_name(ci.Kind), ci.MaxWidth, ci.MaxHeight);
		if (ci.MaxLevel != 0)
			Printf((CONST_STRPTR) ", level %ld.%ld", ci.MaxLevel / 10u, ci.MaxLevel % 10u);
		formats_print("writes", ci.OutputFormats);
		if (VC_HAS_FIELD(ci.Size, struct VCCodecInfo, ChainOutputFormats))
			formats_print("chained", ci.ChainOutputFormats);
		if (VC_HAS_FIELD(ci.Size, struct VCCodecInfo, InputFormats))
			formats_print("reads", ci.InputFormats);
		Printf((CONST_STRPTR) "; %s%s%s, priority %ld\n", ci.Backend, (ci.Flags & VCCF_Session) ? ", session" : "",
		    (ci.Flags & VCCF_Image) ? ", image call" : "", ci.Priority);
		n++;
	}
	Printf((CONST_STRPTR) "%ld codecs\n", n);
	return n != 0 ? RETURN_OK : RETURN_FAIL;
}

/* ---- the summary --------------------------------------------------------------- */

/* The summary's state: the worst outcome so far, and the warnings. */
struct summary
{
	int rc;         /* RETURN_OK, RETURN_WARN, RETURN_ERROR (not installed) or RETURN_FAIL */
	ULONG warnings; /* the WARN lines printed */
};

/**
 * worse() - Note an outcome; the summary keeps the worst.
 * @sum: the summary
 * @rc:  RETURN_WARN, RETURN_ERROR or RETURN_FAIL
 */
static void worse(struct summary *sum, int rc)
{
	if (rc == RETURN_WARN)
		sum->warnings++;
	if (rc > sum->rc)
		sum->rc = rc;
}

/**
 * decoder_row() - A codec driver's first decoder row that sessions serve.
 * @driver: the driver's name, as its rows give it (VCCodecInfo.Backend)
 * @row:    filled with the row
 *
 * Return: TRUE with @row filled, FALSE if the driver has none.
 */
static BOOL decoder_row(const char *driver, struct VCCodecInfo *row)
{
	for (ULONG i = 0;; i++)
	{
		row->Size = sizeof(*row);
		if (VC_QueryCodec(i, row) != 0)
			return FALSE;
		if (row->Kind == VCK_Decoder && (row->Flags & VCCF_Session) != 0 && strcmp((const char *)row->Backend, driver) == 0)
			return TRUE;
	}
}

/**
 * session_cure() - What to do when a codec driver did not open a session.
 * @error: the open's VCERR_*
 *
 * Return: the cure, one line.
 */
static const char *session_cure(LONG error)
{
	switch (error)
	{
	case VCERR_TRANSPORT:
		return "the VideoCore does not answer: run VCHIQInfo, which says why";
	case VCERR_DEVMEM:
		return "the VideoCore's memory is taken: quit other video programs, or raise gpu_mem in the Pi's config.txt";
	case VCERR_NOMEM:
		return "out of memory: quit other programs";
	default:
		return "update the codec driver, or remove it from LIBS:videocodec/";
	}
}

/**
 * summary_session() - Open and close a session of a codec driver's first decoder: the VideoCore answers.
 * @sum:    the summary
 * @driver: the driver's name (VCInfo.Backend)
 */
static void summary_session(struct summary *sum, const char *driver)
{
	struct VCCodecInfo row;
	if (!decoder_row(driver, &row))
	{
		Printf((CONST_STRPTR) "  session:        %s has no decoder to try\n", driver);
		return;
	}
	LONG error = 0;
	struct VCSession *session = VC_OpenSessionTags(VCA_Codec, row.Codec, VCA_Kind, VCK_Decoder, VCA_Backend, (ULONG)driver,
	                                               VC_HAS_FIELD(row.Size, struct VCCodecInfo, Tag) && row.Tag != 0 ? VCA_CodecTag : TAG_IGNORE,
	                                               row.Tag, VCA_ErrorPtr, (ULONG)&error, TAG_DONE);
	if (session != NULL)
	{
		VC_CloseSession(session);
		Printf((CONST_STRPTR) "  session:        %s: its %s decoder opened and closed\n", driver, codec_name(row.Codec));
		return;
	}
	Printf((CONST_STRPTR) "  session:        %s: its %s decoder did not open (error %ld)\n", driver, codec_name(row.Codec), error);
	Printf((CONST_STRPTR) "  FAIL: %s\n", session_cure(error));
	worse(sum, RETURN_FAIL);
}

/**
 * summary_driver() - One codec driver: its codecs and codec memory, and a session of it.
 * @sum: the summary
 * @vi:  what the driver said about itself
 *
 * A driver with no codecs drives hardware this machine lacks (rpivid.codec on
 * a Pi 3, which has no HEVC block): the Install script copies it everywhere,
 * so that is no failure.
 */
static void summary_driver(struct summary *sum, const struct VCInfo *vi)
{
	Printf((CONST_STRPTR) "  codec driver:   %s, %ld codecs", vi->Backend, vi->Codecs);
	if (VC_HAS_FIELD(vi->Size, struct VCInfo, MemFree) && vi->MemTotal != 0)
		Printf((CONST_STRPTR) ", codec memory %ld MiB free of %ld MiB", vi->MemFree >> 20, vi->MemTotal >> 20);
	Printf((CONST_STRPTR) "\n");
	if (vi->Codecs == 0)
	{
		/* a driver whose hardware this machine lacks (rpivid.codec on a Pi 3): it is copied everywhere, nothing fails */
		Printf((CONST_STRPTR) "  session:        %s: none, its hardware is not in this machine\n", vi->Backend);
		return;
	}
	summary_session(sum, (const char *)vi->Backend);
}

/**
 * summary_library() - videocodec.library and its codec drivers.
 * @sum: the summary
 */
static void summary_library(struct summary *sum)
{
	if (VideoCodecBase == NULL)
	{
		Printf((CONST_STRPTR) "  videocodec:     %s did not open\n", VIDEOCODEC_NAME);
		Printf((CONST_STRPTR) "  FAIL: install the video libraries with Kinora's Install script\n");
		worse(sum, RETURN_ERROR);
		return;
	}
	Printf((CONST_STRPTR) "  videocodec:     %s %ld.%ld\n", VIDEOCODEC_NAME, (ULONG)VideoCodecBase->lib_Version,
	    (ULONG)VideoCodecBase->lib_Revision);
	ULONG drivers = 0;
	for (;; drivers++)
	{
		struct VCInfo vi;
		vi.Size = sizeof(vi);
		vi.Counters = NULL; /* no counters here */
		if (VC_GetBackendInfo(drivers, &vi) != 0)
			break;
		summary_driver(sum, &vi);
	}
	if (drivers == 0)
	{
		Printf((CONST_STRPTR) "  codec driver:   none\n");
		Printf((CONST_STRPTR) "  FAIL: copy videocore.codec to LIBS:videocodec/ (Kinora's Install script)\n");
		worse(sum, RETURN_ERROR);
	}
}

#define VCJPEG_CLASS "LIBS:datatypes/vcjpeg.datatype" /* how datatypes.library opens it: LIBS: takes in SYS:Classes */
#define VCJPEG_DESCRIPTOR "SYS:Storage/DataTypes/VCJPEG"
#define VCJPEG_PROBE "T:VCInfo-probe.jpg"
#define DESCRIPTOR_NAME_SIZE 40 /* room for a descriptor's name */

/* A JPEG's start and frame header and nothing else: baseline, 2000x1000, three components */
static const UBYTE probe_jpeg[] = {0xff, 0xd8, 0xff, 0xc0, 0x00, 0x11, 0x08, 0x03, 0xe8, 0x07, 0xd0, 0x03,
                                   0x01, 0x22, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01, 0xff, 0xd9};

/**
 * probe_descriptor() - The descriptor the system picks for a large baseline JPEG: a file of its header alone in T:.
 * @name: filled with the descriptor's name
 * @room: bytes at @name
 *
 * A file, not bytes in memory: some JPEG descriptors' functions examine the
 * file's lock.  Only the header is read; the file is deleted at once.
 *
 * Return: TRUE with @name filled, FALSE if the file could not be written or nothing took it.
 */
static BOOL probe_descriptor(char *name, ULONG room)
{
	BPTR f = Open((CONST_STRPTR)VCJPEG_PROBE, MODE_NEWFILE);
	if (f == 0)
		return FALSE;
	LONG put = Write(f, (APTR)probe_jpeg, sizeof(probe_jpeg));
	Close(f);
	BOOL found = FALSE;
	BPTR lock = put == (LONG)sizeof(probe_jpeg) ? Lock((CONST_STRPTR)VCJPEG_PROBE, ACCESS_READ) : 0;
	if (lock != 0)
	{
		struct DataType *dtn = ObtainDataType(DTST_FILE, (APTR)lock, TAG_DONE);
		if (dtn != NULL)
		{
			strlcpy(name, (const char *)dtn->dtn_Header->dth_Name, room);
			ReleaseDataType(dtn);
			found = TRUE;
		}
		UnLock(lock);
	}
	DeleteFile((CONST_STRPTR)VCJPEG_PROBE);
	return found;
}

/**
 * summary_datatype() - vcjpeg.datatype, when installed: whether its descriptor comes first for JPEGs.
 * @sum: the summary
 */
static void summary_datatype(struct summary *sum)
{
	BPTR cls = Lock((CONST_STRPTR)VCJPEG_CLASS, ACCESS_READ);
	if (cls == 0)
		return; /* not installed: it is optional */
	UnLock(cls);
	char name[DESCRIPTOR_NAME_SIZE];
	if (DataTypesBase == NULL || !probe_descriptor(name, sizeof(name)))
	{
		Printf((CONST_STRPTR) "  JPEG datatype:  vcjpeg.datatype installed; which descriptor takes JPEGs could not be checked (T:)\n");
		return;
	}
	if (strcmp(name, "VCJPEG") == 0)
	{
		Printf((CONST_STRPTR) "  JPEG datatype:  vcjpeg.datatype takes the large JPEGs\n");
		return;
	}
	Printf((CONST_STRPTR) "  JPEG datatype:  large JPEGs go to %s, not vcjpeg.datatype\n", name);
	Printf((CONST_STRPTR) "  WARN: add the line AddDataTypes %s QUIET to S:User-Startup and reboot\n", VCJPEG_DESCRIPTOR);
	worse(sum, RETURN_WARN);
}

/**
 * do_summary() - The setup in plain words: each part OK, or a warning or failure with its cure.
 *
 * Return: RETURN_OK, RETURN_WARN, RETURN_ERROR (a part not installed) or RETURN_FAIL.
 */
static int do_summary(void)
{
	struct summary sum = {RETURN_OK, 0};
	Printf((CONST_STRPTR) "Video setup\n");
	summary_library(&sum);
	if (sum.rc < RETURN_ERROR)
		summary_datatype(&sum);
	if (sum.rc == RETURN_OK)
		Printf((CONST_STRPTR) "PASS\n");
	else if (sum.rc == RETURN_WARN)
		Printf((CONST_STRPTR) "PASS, %ld warning%s\n", sum.warnings, sum.warnings == 1 ? "" : "s");
	else
		Printf((CONST_STRPTR) "FAIL\n");
	return sum.rc;
}

/* ---- main -------------------------------------------------------------------- */

enum
{
	ARG_CODECS,
	ARG_COUNTERS,
	ARG_COUNT
};

/**
 * run_command() - CODECS or COUNTERS, with its verdict.
 * @args: ReadArgs()'s results
 *
 * Return: the command's return code.
 */
static int run_command(const LONG *args)
{
	int rc;
	if (VideoCodecBase == NULL)
	{
		Printf((CONST_STRPTR) "%s did not open\n", VIDEOCODEC_NAME);
		rc = RETURN_ERROR;
	}
	else if (args[ARG_CODECS] != 0)
		rc = do_codecs();
	else
		rc = do_counters();
	Printf((CONST_STRPTR) "%s\n", rc == RETURN_OK ? "PASS" : "FAIL");
	return rc;
}

/**
 * main() - Entry point: with no argument the summary, else one of CODECS or COUNTERS.
 *
 * Both at once are refused.
 *
 * Return: RETURN_OK for a pass, RETURN_WARN, RETURN_ERROR or RETURN_FAIL otherwise.
 */
int main(void)
{
	LONG args[ARG_COUNT] = {0};
	struct RDArgs *rda = ReadArgs((CONST_STRPTR) "CODECS/S,COUNTERS/S", args, NULL);
	if (rda == NULL)
	{
		PrintFault(IoErr(), (CONST_STRPTR) "VCInfo");
		return RETURN_FAIL;
	}
	if (args[ARG_CODECS] != 0 && args[ARG_COUNTERS] != 0)
	{
		Printf((CONST_STRPTR) "one of CODECS or COUNTERS at a time\n");
		FreeArgs(rda);
		return RETURN_FAIL;
	}
	BOOL summary = args[ARG_CODECS] == 0 && args[ARG_COUNTERS] == 0;
	VideoCodecBase = OpenLibrary((CONST_STRPTR)VIDEOCODEC_NAME, 0);
	DataTypesBase = summary ? OpenLibrary((CONST_STRPTR) "datatypes.library", 39) : NULL; /* the summary's datatype check */

	int rc = summary ? do_summary() : run_command(args);

	if (DataTypesBase != NULL)
		CloseLibrary(DataTypesBase);
	if (VideoCodecBase != NULL)
		CloseLibrary(VideoCodecBase);
	FreeArgs(rda);
	return rc;
}
