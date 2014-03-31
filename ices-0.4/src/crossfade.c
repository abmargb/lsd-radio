/* crossfade.c
 * Crossfader plugin
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
 * $Id: crossfade.c 7455 2004-08-03 00:42:04Z brendan $
 */

#include "definitions.h"

static int cf_init(void);
static void cf_new_track(input_stream_t *source);
static int cf_process(int ilen, int16_t* il, int16_t* ir);
static void cf_shutdown(void);

static int resample(unsigned int oldrate, unsigned int newrate);

static ices_plugin_t Crossfader = {
  "crossfade",

  cf_init,
  cf_new_track,
  cf_process,
  cf_shutdown,

  NULL
};

static int Fadelen;
static int FadeSamples;
static int16_t* FL = NULL;
static int16_t* FR = NULL;
static int16_t* Swap = NULL;
static int fpos = 0;
static int flen = 0;

static int NewTrack = 0;

/* public functions */
ices_plugin_t *crossfade_plugin(int secs) {
  Fadelen = secs;
  FadeSamples = secs * 44100;

  return &Crossfader;
}

/* private functions */
static int cf_init(void) {
  if (!(FL = malloc(FadeSamples * 2)))
    goto err;
  if (!(FR = malloc(FadeSamples * 2)))
    goto err;
  if (!(Swap = malloc(FadeSamples * 2)))
    goto err;

  ices_log_debug("Crossfading %d seconds between tracks", Fadelen);
  return 0;

  err:
  ices_log_error("Crossfader could not allocate memory");
  cf_shutdown();
  return -1;
}

static void cf_new_track(input_stream_t *source) {
  static int skipnext = 0;
  static input_stream_t lasttrack;
  int filesecs;

  if (lasttrack.samplerate && lasttrack.samplerate != source->samplerate) {
    if (resample(lasttrack.samplerate, source->samplerate) < 0)
      skipnext = 1;
  }

  memcpy(&lasttrack, source, sizeof(lasttrack));

  /* turn off crossfading for tracks less than twice the length of the fade */
  if (skipnext) {
    skipnext = 0;
    return;
  }

  if (source->filesize && source->bitrate) {
    filesecs = source->filesize / (source->bitrate * 128);
    if (filesecs < 10 || filesecs <= Fadelen * 2) {
      ices_log_debug("crossfade: not fading short track of %d secs", filesecs);
      skipnext = 1;
      return;
    }
  }

  NewTrack = FadeSamples;
}

static int cf_process(int ilen, int16_t* il, int16_t* ir)
{
  int i, j, clen;
  float weight;

  i = 0;
  /* if the buffer is not full, don't attempt to crossfade, just fill it */
  if (flen < FadeSamples)
    NewTrack = 0;

  while (ilen && NewTrack > 0) {
    weight = (float)NewTrack / FadeSamples;
    il[i] = FL[fpos] * weight + il[i] * (1 - weight);
    ir[i] = FR[fpos] * weight + ir[i] * (1 - weight);
    i++;
    fpos = (fpos + 1) % FadeSamples;
    ilen--;
    NewTrack--;
    if (!NewTrack)
      flen = 0;
  }

  j = i;
  while (ilen && flen < FadeSamples) {
    clen = ilen < (FadeSamples - flen) ? ilen : (FadeSamples - flen);
    if (FadeSamples - fpos < clen)
      clen = FadeSamples - fpos;
    memcpy(FL + fpos, il + j, clen * 2);
    memcpy(FR + fpos, ir + j, clen * 2);
    fpos = (fpos + clen) % FadeSamples;
    j += clen;
    flen += clen;
    ilen -= clen;
  }

  while (ilen) {
    clen = ilen < (FadeSamples - fpos) ? ilen : FadeSamples - fpos;
    memcpy(Swap, il + j, clen * 2);
    memcpy(il + i, FL + fpos, clen * 2);
    memcpy(FL + fpos, Swap, clen * 2);
    memcpy(Swap, ir + j, clen * 2);
    memcpy(ir + i, FR + fpos, clen * 2);
    memcpy(FR + fpos, Swap, clen * 2);
    fpos = (fpos + clen) % FadeSamples;
    i += clen;
    j += clen;
    ilen -= clen;
  }

  return i;
}

static void cf_shutdown(void) {
  if (FL) {
    free(FL);
    FL = NULL;
  }
  if (FR) {
    free(FR);
    FR = NULL;
  }
  if (Swap) {
    free(Swap);
    Swap = NULL;
  }

  ices_log_debug("Crossfader shutting down");
}

static int resample(unsigned int oldrate, unsigned int newrate) {
  int16_t* left;
  int16_t* right;
  int16_t* newswap;
  unsigned int newsize = Fadelen * newrate;
  unsigned int newlen;
  int i;
  int off;
  int eps;

  if (!(left = malloc(newsize * sizeof(int16_t))))
    return -1;

  if (!(right = malloc(newsize * sizeof(int16_t)))) {
    free(left);
    return -1;
  }
  if (!(newswap = malloc(newsize * sizeof(int16_t)))) {
    free(left);
    free(right);
    return -1;
  }

  i = 0;
  eps = 0;
  off = (fpos + FadeSamples - flen) % FadeSamples;
  newlen = flen * (float)newrate / oldrate;
  /* the trusty Bresenham algorithm */
  while (i < newlen) {
    left[i] = FL[off];
    right[i] = FR[off];
    eps += oldrate;
    while (eps * 2 >= (int)newrate) {
      off = (off + 1) % FadeSamples;
      eps -= newrate;
    }
    i++;
  }

  free(FL);
  free(FR);
  free(Swap);
  FL = left;
  FR = right;
  Swap = newswap;
  FadeSamples = newsize;
  flen = newlen;
  fpos = i % FadeSamples;

  return 0;
}
