/* in_mp4.c
 * Plugin to read MP4 files as PCM
 *
 * Copyright (c) 2004 Brendan Cully <brendan@xiph.org>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 *
 * $Id: in_mp4.c 7425 2004-07-31 02:32:32Z brendan $
 */

#include "config.h"
#include "in_mp4.h"
#include "metadata.h"

#include <string.h>

/* fink error? */
#define HAVE_IN_PORT_T 1
#define HAVE_SOCKLEN_T 1
#include <mp4.h>
#include <faad.h>

/* -- data structures -- */
typedef struct {
  MP4FileHandle mp4file;
  MP4TrackId track;
  faacDecHandle decoder;
  MP4SampleId cur_sample;
} mp4_in_t;

/* -- static prototypes -- */
static int ices_mp4_readpcm (input_stream_t* self, size_t len,
				int16_t* left, int16_t* right);
static int ices_mp4_close (input_stream_t* self);

/* try to open an MP4 file for decoding. Returns:
 *   0: success
 *   1: not an MP4 file
 *  -1: error opening
 */
int
ices_mp4_open (input_stream_t* self, char* buf, size_t len)
{
  mp4_in_t* mp4_data;
  MP4FileHandle mp4file;
  MP4TrackId track;
  faacDecHandle decoder;
  unsigned int tracks;
  unsigned int i;
  unsigned char *escfg;
  unsigned int escfglen;
  unsigned long samplerate;
  unsigned char channels;
  
  /* At the moment we can only open seekable streams */
  if (! self->filesize)
    return 1;

  if ((mp4file = MP4Read(self->path, 0)) == MP4_INVALID_FILE_HANDLE)
    return 1;

  /* find audio stream */
  track = MP4_INVALID_TRACK_ID;
  tracks = MP4GetNumberOfTracks(mp4file, MP4_AUDIO_TRACK_TYPE, 0);
  for (i = 0; i < tracks; i++) {
    if ((track = MP4FindTrackId(mp4file, i, MP4_AUDIO_TRACK_TYPE, 0)) != MP4_INVALID_TRACK_ID)
      break;
  }
  if (track == MP4_INVALID_TRACK_ID) {
    ices_log_error("ices_mp4_open: No audio track found");
    goto errMP4;
  }

  MP4GetTrackESConfiguration(mp4file, track, &escfg, &escfglen);
  if (!escfg) {
    ices_log_error("ices_mp4_open: No audio format information found");
    goto errMP4;
  }

  if (!(decoder = faacDecOpen())) {
    ices_log_error("ices_mp4_open: Could not get a FAAD handle");
    goto errMP4;
  }

  if (faacDecInit2(decoder, escfg, escfglen, &samplerate, &channels) < 0) {
    ices_log_error("ices_mp4_open: Could not initialise FAAD");
    free(escfg);
    goto errFAAC;
  }
  free(escfg);

  ices_log_debug("Found MP4 audio at track %u, sample rate %u, %u channels", track, samplerate, channels);

  if (channels != 2) {
    ices_log_error("ices_mp4_open: Bad number of channels");
    goto errFAAC;
  }

  if (!(mp4_data = (mp4_in_t*)malloc (sizeof (mp4_in_t)))) {
    ices_log_error ("Malloc failed in ices_mp4_open");
    goto errFAAC;
  }

  close(self->fd);

  self->samplerate = samplerate;
  self->channels = channels;

  mp4_data->mp4file = mp4file;
  mp4_data->track = track;
  mp4_data->decoder = decoder;
  mp4_data->cur_sample = 1;

  self->type = ICES_INPUT_MP4;
  self->data = mp4_data;

  self->read = NULL;
  self->readpcm = ices_mp4_readpcm;
  self->close = ices_mp4_close;

  return 0;

errFAAC:
  faacDecClose(decoder);
errMP4:
  MP4Close(mp4file);

  return -1;
}

static int
ices_mp4_readpcm (input_stream_t* self, size_t olen, int16_t* left,
		     int16_t* right)
{
  mp4_in_t* mp4_data = (mp4_in_t*)self->data;
  unsigned char* buf;
  unsigned int blen;
  faacDecFrameInfo fi;
  void* decbuf;
  int i;

  fi.samples = 0;
  while (fi.samples == 0) {
    buf = NULL;
    if (!MP4ReadSample(mp4_data->mp4file, mp4_data->track, mp4_data->cur_sample++,
		       &buf, &blen, NULL, NULL, NULL, NULL) || !blen)
    {
      ices_log_error("Error reading MP4");
      return 0;
    }

    decbuf = faacDecDecode(mp4_data->decoder, &fi, buf, blen);
    free (buf);
    if (fi.error) {
      ices_log_error("Error decoding MP4: %s", faacDecGetErrorMessage(fi.error));
      return 0;
    }

  }
  i = 0;
  while (i < fi.samples * 2) {
    *left++ = ((int16_t*)decbuf)[i++];
    *right++ = ((int16_t*)decbuf)[i++];
  }
  
  return fi.samples / 2;
}

static int
ices_mp4_close (input_stream_t* self)
{
  mp4_in_t* mp4_data = (mp4_in_t*) self->data;

  faacDecClose(mp4_data->decoder);
  MP4Close(mp4_data->mp4file);
  free (mp4_data);

  return 0;
}
