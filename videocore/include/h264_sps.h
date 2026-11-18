/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * h264_sps.h - what the backend reads from an H.264 sequence header (SPS)
 * itself (h264_sps.c).
 *
 * The VPU's decoder refuses nothing it decodes wrong and says nothing when
 * it has no memory, so the profile and the size are checked before the
 * stream reaches it; and its format change says 1/1 for the pixel aspect
 * whatever the stream says, and "JFIF" for any full-range stream whatever
 * its matrix, so the aspect and the colour space come from here.
 */
#ifndef H264_SPS_H
#define H264_SPS_H

#include <exec/types.h>
#include <types.h>
#include <libraries/videocodec.h>
#include <libraries/videocodec_backend.h>

/* What the backend reads from an H.264 SPS */
struct h264_sps
{
	u32 profile;           /* profile_idc, 0 for no SPS */
	u32 ref_frames;        /* max_num_ref_frames */
	u32 macroblocks;       /* of a frame, 0 for an SPS cut short */
	struct VCRational par; /* the pixel aspect its VUI gives, 0/0 for none */
	ULONG color_space;     /* VCCS_* its VUI names, guessed from its rows where it names none; VCCS_Unknown for no SPS or one cut short */
};

/* The first SPS in a piece of an Annex-B stream: its profile, size, pixel aspect and colour space */
void h264_sps_read(const UBYTE *data, u32 length, struct h264_sps *sps);

#endif /* H264_SPS_H */
