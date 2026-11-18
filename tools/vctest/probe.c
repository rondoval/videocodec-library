/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * probe.c - PROBE: a codec backend's own refusals, its entry points called
 * directly, past videocodec.library, with what no program may hand them: a
 * structure too short for its fields, a row past the table's end, no
 * parameters, no session.  Every backend must refuse each of these cleanly;
 * the library checks most of them itself, so only a direct call reaches the
 * backend's own checks.  A backend whose rows serve no image call must also
 * refuse VCB_Image().
 *
 * Each call's answer is printed as probe.<call>=<rc>: the suite judges them.
 */
#ifdef __INTELLISENSE__
#include <clib/exec_protos.h>
#include <clib/videocodec_backend_protos.h>
#else
#include <proto/exec.h>
#include <proto/videocodec_backend.h>
#endif

#include <dos/dos.h>

#include <string.h>

#include <emu68test/kv.h>
#include <libraries/videocodec_backend.h>
#include <strutil.h>

#include "commands.h"

const char probe_template[] = "NAME/A";

#define TOO_SHORT 4u     /* a structure's Size that ends before its first field */
#define PATH_BYTES 64u   /* the backend's path: videocodec/<name> */
#define NOT_A_SESSION ((APTR)0x10) /* a handle no backend ever handed out */

struct Library *VCBackendBase; /* the backend probed, for its VCB_* calls */

/**
 * probe_info() - VCB_GetInfo() and VCB_QueryCodec() with short structures and a row past the end.
 *
 * Return: whether one of the backend's rows serves the image calls (VCCF_Image).
 */
static BOOL probe_info(void)
{
	struct VCInfo info;
	memset(&info, 0, sizeof(info));
	info.Size = TOO_SHORT;
	kv_num("probe.getinfo_short", VCB_GetInfo(&info));
	info.Size = sizeof(info);
	kv_num("probe.getinfo", VCB_GetInfo(&info));
	kv_str("probe.backend", (const char *)info.Backend);
	kv_unum("probe.codecs", info.Codecs);
	struct VCCodecInfo row;
	memset(&row, 0, sizeof(row));
	row.Size = TOO_SHORT;
	kv_num("probe.querycodec_short", VCB_QueryCodec(0, &row));
	row.Size = sizeof(row);
	kv_num("probe.querycodec_past", VCB_QueryCodec(info.Codecs, &row));
	BOOL images = FALSE;
	for (ULONG index = 0; index < info.Codecs; index++)
	{
		row.Size = sizeof(row);
		images |= VCB_QueryCodec(index, &row) == 0 && (row.Flags & VCCF_Image) != 0;
	}
	kv_bool("probe.images", images);
	return images;
}

/**
 * probe_sessions() - The session calls with no parameters and with a handle no session has.
 */
static void probe_sessions(void)
{
	LONG error = 0;
	struct VCSessionParams params;
	memset(&params, 0, sizeof(params));
	params.Size = TOO_SHORT;
	kv_bool("probe.open_null", VCB_OpenSession(NULL, &error) == NULL);
	kv_num("probe.open_null_error", error);
	kv_bool("probe.open_short", VCB_OpenSession(&params, &error) == NULL);
	kv_num("probe.open_short_error", error);
	struct VCPacket packet;
	struct VCFrame frame;
	struct VCItem item;
	memset(&packet, 0, sizeof(packet));
	memset(&frame, 0, sizeof(frame));
	packet.Size = sizeof(packet);
	frame.Size = sizeof(frame);
	kv_num("probe.sendpacket_null", VCB_SendPacket(NOT_A_SESSION, NULL));
	kv_num("probe.sendpacket", VCB_SendPacket(NOT_A_SESSION, &packet));
	kv_num("probe.sendframe", VCB_SendFrame(NOT_A_SESSION, &frame));
	kv_num("probe.flush", VCB_Flush(NOT_A_SESSION));
	kv_num("probe.setattrs_null", VCB_SetAttrs(NOT_A_SESSION, NULL));
	kv_num("probe.setattrs_short", VCB_SetAttrs(NOT_A_SESSION, &params));
	kv_num("probe.poll", VCB_Poll(NOT_A_SESSION, &item));
	kv_bool("probe.importpacket", VCB_ImportPacket(NOT_A_SESSION, VCS_Input, &packet, sizeof(packet)) == NULL);
	kv_bool("probe.importframe", VCB_ImportFrame(NOT_A_SESSION, VCS_Output, &frame) == NULL);
	kv_bool("probe.outputframe", VCB_OutputFrame(NOT_A_SESSION, 0) == NULL);
	VCB_ReleasePacket(NOT_A_SESSION, &packet);
	VCB_ReleaseFrame(NOT_A_SESSION, &frame);
	VCB_CloseSession(NOT_A_SESSION);
	kv_bool("probe.releases", TRUE); /* reached: the releases and the close of no session did nothing */
}

/**
 * probe_image() - VCB_Image() at a backend that serves no image call: refused.
 * @images: whether a row of it serves the image calls: then nothing is asked
 */
static void probe_image(BOOL images)
{
	struct VCImageParams params;
	memset(&params, 0, sizeof(params));
	params.Size = sizeof(params);
	params.Kind = VCK_Decoder;
	if (images)
		kv_str("probe.image", "not asked");
	else
		kv_num("probe.image", VCB_Image(&params));
}

/**
 * do_probe() - PROBE: a backend's refusals, its entry points called directly.
 * @t:    the tool
 * @args: probe_template's: NAME, the backend's file in LIBS:videocodec (rpivid.codec)
 *
 * Return: RETURN_OK when every call came back; RETURN_ERROR when the backend did not open.
 */
int do_probe(struct tool *t, LONG *args)
{
	(void)t;
	char path[PATH_BYTES];
	const ULONG drawer = sizeof(VIDEOCODEC_BACKEND_DRAWER "/") - 1u;
	strlcpy(path, VIDEOCODEC_BACKEND_DRAWER "/", sizeof(path));
	strlcpy(path + drawer, (const char *)args[0], sizeof(path) - drawer);
	kv_str("probe.path", path);
	VCBackendBase = OpenLibrary((CONST_STRPTR)path, 0);
	if (VCBackendBase == NULL)
	{
		kv_str("fail", "the backend did not open");
		return RETURN_ERROR;
	}
	probe_image(probe_info());
	probe_sessions();
	CloseLibrary(VCBackendBase);
	VCBackendBase = NULL;
	return RETURN_OK;
}
