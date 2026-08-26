package com.videoai.monitoring.core.support;

import org.springframework.stereotype.Component;

import java.util.Arrays;

@Component
public class VectorSql {
    public String toVectorLiteral(float[] vector) {
        if (vector == null || vector.length != 512) {
            throw new IllegalArgumentException("embedding must contain exactly 512 values");
        }
        StringBuilder builder = new StringBuilder("[");
        for (int i = 0; i < vector.length; i++) {
            if (i > 0) {
                builder.append(',');
            }
            builder.append(Float.toString(vector[i]));
        }
        return builder.append(']').toString();
    }

    public float[] normalize(float[] vector) {
        double norm = 0.0;
        for (float value : vector) {
            norm += value * value;
        }
        if (norm == 0.0) {
            return Arrays.copyOf(vector, vector.length);
        }
        float[] normalized = new float[vector.length];
        double scale = Math.sqrt(norm);
        for (int i = 0; i < vector.length; i++) {
            normalized[i] = (float) (vector[i] / scale);
        }
        return normalized;
    }
}
