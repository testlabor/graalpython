/*
 * Copyright (c) 2021, Oracle and/or its affiliates. All rights reserved.
 * DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
 *
 * The Universal Permissive License (UPL), Version 1.0
 *
 * Subject to the condition set forth below, permission is hereby granted to any
 * person obtaining a copy of this software, associated documentation and/or
 * data (collectively the "Software"), free of charge and under any and all
 * copyright rights in the Software, and any and all patent rights owned or
 * freely licensable by each licensor hereunder covering either (i) the
 * unmodified Software as contributed to or provided by such licensor, or (ii)
 * the Larger Works (as defined below), to deal in both
 *
 * (a) the Software, and
 *
 * (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
 * one is included with the Software each a "Larger Work" to which the Software
 * is contributed by such licensors),
 *
 * without restriction, including without limitation the rights to copy, create
 * derivative works of, display, perform, and distribute the Software and make,
 * use, sell, offer for sale, import, export, have made, and have sold the
 * Software and the Larger Work(s), and to sublicense the foregoing rights on
 * either these or other terms.
 *
 * This license is subject to the following condition:
 *
 * The above copyright notice and either this complete permission notice or at a
 * minimum a reference to the UPL must be included in all copies or substantial
 * portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
package com.oracle.graal.python.builtins.objects.itertools;

import com.oracle.graal.python.annotations.ArgumentClinic;
import static com.oracle.graal.python.builtins.PythonBuiltinClassType.ValueError;
import static com.oracle.graal.python.nodes.ErrorMessages.S_MUST_BE_S;
import static com.oracle.graal.python.nodes.ErrorMessages.TDATAOBJECT_SHOULDNT_HAVE_NEXT;
import static com.oracle.graal.python.nodes.ErrorMessages.TDATAOBJECT_SHOULD_NOT_HAVE_MORE_LINKS;
import static com.oracle.graal.python.nodes.SpecialMethodNames.__COPY__;
import static com.oracle.graal.python.nodes.SpecialMethodNames.__INIT__;
import static com.oracle.graal.python.nodes.SpecialMethodNames.__REDUCE__;

import java.util.List;

import com.oracle.graal.python.builtins.Builtin;
import com.oracle.graal.python.builtins.CoreFunctions;
import com.oracle.graal.python.builtins.PythonBuiltinClassType;
import com.oracle.graal.python.builtins.PythonBuiltins;
import com.oracle.graal.python.builtins.modules.BuiltinFunctions.LenNode;
import com.oracle.graal.python.builtins.objects.PNone;
import com.oracle.graal.python.builtins.objects.list.PList;
import com.oracle.graal.python.builtins.objects.object.PythonObject;
import com.oracle.graal.python.builtins.objects.tuple.PTuple;
import com.oracle.graal.python.nodes.call.special.LookupAndCallUnaryNode;
import com.oracle.graal.python.nodes.function.PythonBuiltinBaseNode;
import com.oracle.graal.python.nodes.function.builtins.PythonQuaternaryClinicBuiltinNode;
import com.oracle.graal.python.nodes.function.builtins.PythonUnaryBuiltinNode;
import com.oracle.graal.python.nodes.function.builtins.clinic.ArgumentClinicProvider;
import com.oracle.graal.python.nodes.object.GetClassNode;
import com.oracle.graal.python.util.PythonUtils;
import com.oracle.truffle.api.dsl.Cached;
import com.oracle.truffle.api.dsl.GenerateNodeFactory;
import com.oracle.truffle.api.dsl.NodeFactory;
import com.oracle.truffle.api.dsl.Specialization;
import com.oracle.truffle.api.frame.VirtualFrame;
import com.oracle.truffle.api.profiles.BranchProfile;

@CoreFunctions(extendClasses = {PythonBuiltinClassType.PTeeDataObject})
public class TeeDataObjectBuiltins extends PythonBuiltins {

    static final int LINKCELLS = 128;

    @Override
    protected List<? extends NodeFactory<? extends PythonBuiltinBaseNode>> getNodeFactories() {
        return TeeDataObjectBuiltinsFactory.getFactories();
    }

    @Builtin(name = __INIT__, minNumOfPositionalArgs = 1, parameterNames = {"$self", "it", "values", "nxt"})
    @ArgumentClinic(name = "values", defaultValue = "PNone.NONE", useDefaultForNone = true)
    @ArgumentClinic(name = "nxt", defaultValue = "PNone.NONE", useDefaultForNone = true)
    @GenerateNodeFactory
    public abstract static class InitNode extends PythonQuaternaryClinicBuiltinNode {

        @Override
        protected ArgumentClinicProvider getArgumentClinic() {
            return TeeDataObjectBuiltinsClinicProviders.InitNodeClinicProviderGen.INSTANCE;
        }

        abstract Object execute(VirtualFrame frame, PTeeDataObject self, Object it, Object values, Object nxt);

        @Specialization(guards = "isNone(values)")
        Object init(PTeeDataObject self, Object it, @SuppressWarnings("unused") Object values, Object nxt) {
            self.setIt(it);
            self.setValues(factory().createList());
            self.setNumread(0);
            self.setRunning(false);
            self.setNextlink(nxt);
            return PNone.NONE;
        }

        @Specialization(guards = "!isNone(values)")
        Object init(VirtualFrame frame, PTeeDataObject self, Object it, Object values, Object nxt,
                        @Cached LenNode lenNode,
                        @Cached BranchProfile numreadLCProfile,
                        @Cached BranchProfile numreadTooHighProfile,
                        @Cached BranchProfile nxtNotDOProfile,
                        @Cached BranchProfile nxtNotNoneProfile) {
            self.setIt(it);
            self.setValues((PList) values);
            int numread = (int) lenNode.call(frame, values);
            if (numread == LINKCELLS) {
                numreadLCProfile.enter();
                if (!(nxt instanceof PTeeDataObject)) {
                    nxtNotDOProfile.enter();
                    throw raise(ValueError, S_MUST_BE_S, "_tee_dataobject next link", "_tee_dataobject");
                }
                self.setNextlink(nxt);
            } else if (numread > LINKCELLS) {
                numreadTooHighProfile.enter();
                throw raise(ValueError, TDATAOBJECT_SHOULD_NOT_HAVE_MORE_LINKS, LINKCELLS);
            } else if (!(nxt instanceof PNone)) {
                nxtNotNoneProfile.enter();
                throw raise(ValueError, TDATAOBJECT_SHOULDNT_HAVE_NEXT);
            }
            self.setNumread(numread);
            self.setRunning(false);
            self.setNextlink(nxt);
            return PNone.NONE;
        }

        protected LookupAndCallUnaryNode createCopyNode() {
            return LookupAndCallUnaryNode.create(__COPY__);
        }
    }

    @Builtin(name = __REDUCE__, minNumOfPositionalArgs = 1)
    @GenerateNodeFactory
    public abstract static class ReduceNode extends PythonUnaryBuiltinNode {
        abstract Object execute(VirtualFrame frame, PythonObject self);

        @Specialization
        Object reduce(PTeeDataObject self,
                        @Cached GetClassNode getClass) {
            int numread = self.getNumread();
            Object[] values = new Object[numread];
            PythonUtils.arraycopy(self.getValues(), 0, values, 0, numread);
            Object type = getClass.execute(self);
            Object nextlink = self.getNextlink();
            PTuple tuple = factory().createTuple(new Object[]{self.getIt(), factory().createList(values), nextlink == null ? PNone.NONE : nextlink});
            return factory().createTuple(new Object[]{type, tuple});
        }
    }
}
