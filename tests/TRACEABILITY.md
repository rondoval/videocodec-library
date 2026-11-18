# emu68-vchiq-library: traceability

Written by the suite's host tier (`run.sh host` rewrites it): every item the suite must cover, with the tests that cover it.

**Uncovered: 0** of 74 items; known gaps: 0.

## videocodec.library

| Item | Tests |
|---|---|
| VC_OpenSession | `test_decoder.py::test_bit_exact` |
| VC_CloseSession | `test_decoder.py::test_bit_exact` |
| VC_ImportPacket | `test_decoder.py::test_imported_packets` |
| VC_ImportFrame | `test_decoder.py::test_imported_frames`, `test_images.py::test_converter_session_rate` |
| VC_SendPacket | `test_decoder.py::test_bit_exact` |
| VC_SendFrame | `test_encoder.py::test_h264_encode` |
| VC_Poll | `test_decoder.py::test_bit_exact` |
| VC_ReleaseFrame | `test_decoder.py::test_bit_exact` |
| VC_ReleasePacket | `test_encoder.py::test_h264_encode` |
| VC_Flush | `test_decoder.py::test_flush_replays` |
| VC_SetAttrs | `test_decoder.py::test_resignal`, `test_encoder.py::test_key_frame_on_request` |
| VC_QueryCodec | `test_device.py::test_codec_table` |
| VC_GetBackendInfo | `test_device.py::test_connection_up` |
| VC_DecodeImage | `test_images.py::test_jpeg_decode` |
| VC_EncodeImage | `test_images.py::test_jpeg_encode` |
| VC_ConvertImage | `test_images.py::test_convert_rgb16_720p` |
| VC_GetImageInfo | `test_images.py::test_image_header` |
| VC_CodecOfTag | `test_vcinfo.py::test_codec_of_tag` |

## vchiq.device commands

| Item | Tests |
|---|---|
| NSCMD_DEVICEQUERY | `test_device.py::test_device_query` |
| NSCMD_VQ_GETINFO | `test_device.py::test_connection_up` |
| NSCMD_VQ_TEST_ABANDON | `test_resets.py::test_abandon_then_repair` |
| CMD_FLUSH | `test_device.py::test_flush_gives_back_the_reads` |
| CMD_READ | `test_device.py::test_audio_bulk` |
| CMD_WRITE | `test_device.py::test_audio_bulk` |
| NSCMD_VQ_BULKWRITE | `test_device.py::test_audio_bulk` |
| NSCMD_VQ_BULKREAD | `test_decoder.py::test_bit_exact` |

## Tags

| Item | Tests |
|---|---|
| VCA_Codec | `test_decoder.py::test_bit_exact` |
| VCA_Kind | `test_decoder.py::test_bit_exact` |
| VCA_CodecTag | `test_decoder.py::test_codec_tag` |
| VCA_SigMask | `test_decoder.py::test_bit_exact` |
| VCA_SigTask | `test_decoder.py::test_bit_exact` |
| VCA_ErrorPtr | `test_decoder.py::test_bit_exact` |
| VCA_Backend | `test_decoder.py::test_backend_named` |
| VCA_Width | `test_encoder.py::test_h264_encode` |
| VCA_Height | `test_encoder.py::test_h264_encode` |
| VCA_InputFormat | `test_encoder.py::test_h264_encode` |
| VCA_InputPitch | `test_images.py::test_convert_rgb16_720p` |
| VCA_SourceRect | `test_images.py::test_convert_part_of_the_picture` |
| VCA_OutputFormat | `test_colour.py::test_a_stream_keeps_its_colours`, `test_decoder.py::test_chained_output` |
| VCA_OutputWidth | `test_encoder.py::test_scaled_through_the_isp` |
| VCA_OutputHeight | `test_encoder.py::test_scaled_through_the_isp` |
| VCA_OutputPitch | `test_images.py::test_jpeg_decode` |
| VCA_DestRect | `test_datatype.py::test_pixels`, `test_images.py::test_jpeg_decode_to_a_place` |
| VCA_KeepAspect | `test_players.py::test_pixel_aspect_on_screen` |
| VCA_InputCount | `test_decoder.py::test_bit_exact` |
| VCA_InputSize | `test_decoder.py::test_bit_exact` |
| VCA_OutputCount | `test_encoder.py::test_h264_encode` |
| VCA_OutputSize | `test_encoder.py::test_h264_encode` |
| VCA_Framed | `test_decoder.py::test_bit_exact_framed` |
| VCA_Extradata | `test_decoder.py::test_extradata` |
| VCA_ExtradataSize | `test_decoder.py::test_extradata` |
| VCA_FrameRateNum | `test_decoder.py::test_bit_exact` |
| VCA_FrameRateDen | `test_decoder.py::test_bit_exact` |
| VCA_Bitrate | `test_encoder.py::test_h264_encode` |
| VCA_RateControl | `test_encoder.py::test_a_constant_rate_refused`, `test_encoder.py::test_a_variable_rate` |
| VCA_KeyInterval | `test_encoder.py::test_h264_encode` |
| VCA_Profile | `test_encoder.py::test_the_profile_asked_for` |
| VCA_Level | `test_encoder.py::test_the_level_asked_for` |
| VCA_Quality | `test_images.py::test_jpeg_encode` |
| VCA_RequestKeyFrame | `test_encoder.py::test_key_frame_on_request` |
| VCA_ColorSpace | `test_colour.py::test_a_converter_is_told_the_colours`, `test_colour.py::test_the_client_overrules_the_stream`, `test_encoder.py::test_the_color_space_written` |
| VCA_Data | `test_images.py::test_jpeg_decode` |
| VCA_Length | `test_images.py::test_jpeg_decode` |
| VCA_Dest | `test_images.py::test_jpeg_decode` |
| VCA_DestSize | `test_images.py::test_jpeg_encode` |
| VCA_Timeout | `test_images.py::test_image_call_gives_up_at_its_timeout` |

## VCGrab's settings file

| Item | Tests |
|---|---|
| settings: TO | `test_vcgrab.py::test_saved_settings` |
| settings: SIZE | `test_vcgrab.py::test_saved_settings` |
| settings: FPS | `test_vcgrab.py::test_saved_settings` |
| settings: BITRATE | `test_vcgrab.py::test_saved_settings` |
| settings: SECONDS | `test_vcgrab.py::test_a_key_turned_off` |
| settings: STARTKEY | `test_vcgrab.py::test_saved_settings` |
| settings: STOPKEY | `test_vcgrab.py::test_saved_settings` |
| settings: STILLKEY | `test_vcgrab.py::test_a_saved_still_key` |
